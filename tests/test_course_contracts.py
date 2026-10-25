"""Read-only browsing and honest unfinished responses work without credentials/DB."""
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.leave_web import create_app
from app.main import app as extraction_app
from app.course.checks import check_day


class CourseContracts(unittest.TestCase):
    def test_reader_needs_no_database(self):
        with patch('app.leave_web.connect_database',side_effect=AssertionError('reader must not connect')),TestClient(create_app()) as client:
            value=client.get('/api/course')
            self.assertEqual(value.status_code,200)
            self.assertEqual(len(value.json()['lessons']),26)
            self.assertEqual(client.get('/api/me').status_code,401)
            self.assertEqual(client.get('/course').status_code,200)
            for resource in value.json()['resources']:
                with self.subTest(resource=resource['path']):
                    self.assertEqual(client.get('/api/course/files',params={'path':resource['path']}).status_code,200)

    def test_unimplemented_is_not_fake_success(self):
        with patch('app.main.build_messages',side_effect=NotImplementedError('pending')),TestClient(extraction_app) as client:
            response=client.post('/api/leave/parse',json={'text':'请假','referenceTime':'2026-10-25T09:00:00+08:00'})
            self.assertEqual(response.status_code,501)

    def test_foundation_examples_are_not_completion(self):
        for day in range(1,12):
            with self.subTest(day=day):
                value=check_day(day,'reference')
                self.assertEqual(value['status'],'passed',value)
                self.assertFalse(value['completion_eligible'])


if __name__=='__main__':unittest.main()
