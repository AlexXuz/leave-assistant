"""助教资料生成脚本；使用 Codex 附带 Python/reportlab，不是学生运行依赖。"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "ingestion_lab" / "travel-policy.pdf"


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("LabChinese", r"C:\Windows\Fonts\msyh.ttc", subfontIndex=0))
    title = ParagraphStyle("LabTitle", fontName="LabChinese", fontSize=18, leading=28, spaceAfter=16,
                           textColor=colors.black, alignment=TA_LEFT, wordWrap="CJK")
    heading = ParagraphStyle("LabHeading", fontName="LabChinese", fontSize=13, leading=22,
                             spaceBefore=14, spaceAfter=8, textColor=colors.black, wordWrap="CJK")
    body = ParagraphStyle("LabBody", fontName="LabChinese", fontSize=10.5, leading=20, spaceAfter=10,
                          textColor=colors.black, wordWrap="CJK")
    note = ParagraphStyle("LabNote", parent=body, fontSize=8, leading=14, textColor=colors.HexColor("#525252"))
    story = [Paragraph("青禾实验室差旅制度", title),
             Paragraph("文档 ID：travel-policy<br/>版本：2026-10-21-v1", note),
             Paragraph("本制度说明差旅住宿标准、申请审批和报销凭证要求。以下资料仅供 AI 应用开发教学使用。", body),
             Paragraph("住宿报销上限", heading),
             Paragraph("北京和上海的住宿报销上限为每人每晚 520 元。", body),
             Paragraph("其他城市的住宿报销上限为每人每晚 380 元。", body),
             Paragraph("超过上限的住宿，需要在预订前取得部门经理的书面批准。", body),
             Spacer(1, 12),
             Paragraph("阅读示例：查询上海出差的住宿上限时，应能追溯到本页。", note),
             PageBreak(),
             Paragraph("差旅申请与报销", title),
             Paragraph("文档 ID：travel-policy<br/>版本：2026-10-21-v1", note),
             Paragraph("申请与凭证", heading),
             Paragraph("员工应在出差前提交差旅申请，并由直属主管审批。", body),
             Paragraph("报销住宿费用时，需要提交对应的住宿发票和订单记录。", body),
             Paragraph("本教学文件没有提供员工个人报销记录，也没有说明机票升舱或每日餐费标准。", body),
             Spacer(1, 12),
             Paragraph("阅读示例：查询住宿报销所需凭证时，应能追溯到本页；缺少的制度规定不能自行推断。", note)]

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("LabChinese", 8)
        canvas.setFillColor(colors.HexColor("#525252"))
        canvas.drawString(38, 25, "虚构教学资料")
        canvas.drawRightString(A5[0] - 38, 25, f"第 {document.page} 页")
        canvas.restoreState()

    SimpleDocTemplate(str(OUTPUT), pagesize=A5, leftMargin=38, rightMargin=38,
                      topMargin=35, bottomMargin=45, title="青禾实验室差旅制度", author="AI 应用开发项目课").build(
                          story, onFirstPage=footer, onLaterPages=footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
