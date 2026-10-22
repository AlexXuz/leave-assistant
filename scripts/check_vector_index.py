"""助教提供的索引验收：临时目录、合成单位向量，零模型调用。"""

import copy
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

import app.indexing as indexing
import app.file_rag_baseline as rag
import app.vector_index as storage


def assert_rejected(action, message):
    try:
        action()
    except storage.IndexValidationError:
        return
    raise AssertionError(message)


def main() -> int:
    chunks = storage.load_current_chunks()
    dimension = storage.current_embedding_config()["dimension"]
    vectors = np.eye(len(chunks), dimension, dtype=np.float32)
    try:
        with tempfile.TemporaryDirectory() as directory, patch.object(storage, "INDEX_PATH", Path(directory) / "test-index.npz"):
            with patch.object(indexing, "embed_documents", return_value=vectors) as document_encoder:
                manifest = indexing.build_policy_index()
                document_encoder.assert_called_once_with([chunk["content"] for chunk in chunks])
            stored_chunks, stored_vectors, stored_manifest = storage.load_index()
            assert stored_chunks == chunks and np.array_equal(stored_vectors, vectors)
            assert manifest == stored_manifest, "构建函数应返回 save_index 的清单"
            print("PASS: 文档按顺序编码一次，片段、向量、清单保存并正确读回")

            # 任何查询文档编码都会被拦截；问题编码使用明确的合成向量。
            with patch.object(rag, "embed_documents", side_effect=AssertionError("查询阶段不应重新编码文档"), create=True), patch.object(rag, "embed_query", return_value=vectors[1]) as query_encoder:
                for question in ("第一次查询", "第二次查询"):
                    prepared = rag.prepare_rag_request(question, top_k=2)
                    assert prepared["retrieved_chunks"][0]["chunk"]["id"] == chunks[1]["id"]
                    expected = [{"id": row["chunk"]["id"], "content": row["chunk"]["content"]} for row in prepared["retrieved_chunks"]]
                    assert prepared["documents"] == expected
                assert query_encoder.call_count == 2, "每个查询应编码一次问题"
            print("PASS: 连续查询复用文档向量，只编码问题，来源仍对应命中片段")

            changed_config = copy.deepcopy(storage.current_embedding_config())
            changed_config["model"] = "another-model-with-the-same-dimension"
            with patch.object(storage, "current_embedding_config", return_value=changed_config):
                assert_rejected(storage.load_index, "模型变化但维度相同时仍应拒绝旧索引")
            with patch.object(storage, "source_fingerprint", return_value="changed-source-content"):
                assert_rejected(storage.load_index, "原文变化应拒绝旧索引")

            # 仅改临时索引，验证向量行被交换也会被发现。
            original_bytes = storage.INDEX_PATH.read_bytes()
            with np.load(storage.INDEX_PATH, allow_pickle=False) as archive:
                payload = {key: archive[key].copy() for key in archive.files}
            payload["vectors"][[0, 1]] = payload["vectors"][[1, 0]]
            np.savez_compressed(storage.INDEX_PATH, **payload)
            assert_rejected(storage.load_index, "向量行被交换应被发现")
            storage.INDEX_PATH.write_bytes(original_bytes)
            print("PASS: 模型配置变化、原文变化、向量行数据变化均拒绝继续使用")
    except NotImplementedError as error:
        print(f"待完成：{error}；零模型调用")
        return 2
    except (AssertionError, storage.IndexValidationError) as error:
        print(f"FAIL: {error}；零模型调用")
        return 1
    print("索引本地验收通过；使用合成向量，未生成正式索引，未验证真实检索效果。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
