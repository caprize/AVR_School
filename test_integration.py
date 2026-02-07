#!/usr/bin/env python3
"""
Chemistry Bot - Integration tests
Tests bot functionality without actual Telegram API calls
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from database import DatabaseManager
import json


class TestDatabaseManager(unittest.TestCase):
    """Test DatabaseManager class"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager()
        # Clear test data
        self.db.clear_all_data()
    
    def tearDown(self):
        """Clean up test data"""
        self.db.clear_all_data()
    
    def test_redis_connection(self):
        """Test Redis connection"""
        self.assertTrue(self.db.is_redis_connected())
    
    def test_add_student(self):
        """Test adding a student"""
        result = self.db.add_student(123, "testuser", "пн,ср 15:00")
        self.assertTrue(result)
        
        student = self.db.get_student(123)
        self.assertIsNotNone(student)
        self.assertEqual(student['username'], "testuser")
        self.assertEqual(student['schedule'], "пн,ср 15:00")
    
    def test_get_nonexistent_student(self):
        """Test getting a non-existent student"""
        student = self.db.get_student(999999)
        self.assertIsNone(student)
    
    def test_update_student(self):
        """Test updating a student"""
        self.db.add_student(123, "testuser", "пн,ср 15:00")
        
        result = self.db.update_student(123, schedule="вт,чт 17:00")
        self.assertTrue(result)
        
        student = self.db.get_student(123)
        self.assertEqual(student['schedule'], "вт,чт 17:00")
    
    def test_delete_student(self):
        """Test deleting a student"""
        self.db.add_student(123, "testuser", "пн,ср 15:00")
        
        result = self.db.delete_student(123)
        self.assertTrue(result)
        
        student = self.db.get_student(123)
        self.assertIsNone(student)
    
    def test_get_all_students(self):
        """Test getting all students"""
        self.db.add_student(123, "user1", "пн 15:00")
        self.db.add_student(456, "user2", "вт 17:00")
        
        students = self.db.get_all_students()
        self.assertEqual(len(students), 2)
    
    def test_add_lecture(self):
        """Test adding a lecture"""
        result = self.db.add_lecture("lec1", "Основы химии", "basics.pdf", "/path/basics.pdf")
        self.assertTrue(result)
        
        lecture = self.db.get_lecture("lec1")
        self.assertIsNotNone(lecture)
        self.assertEqual(lecture['name'], "Основы химии")
    
    def test_get_all_lectures(self):
        """Test getting all lectures"""
        self.db.add_lecture("lec1", "Основы", "basics.pdf", "/path/basics.pdf")
        self.db.add_lecture("lec2", "Органическая", "organic.pdf", "/path/organic.pdf")
        
        lectures = self.db.get_all_lectures()
        self.assertEqual(len(lectures), 2)
    
    def test_delete_lecture(self):
        """Test deleting a lecture"""
        self.db.add_lecture("lec1", "Основы", "basics.pdf", "/path/basics.pdf")
        
        result = self.db.delete_lecture("lec1")
        self.assertTrue(result)
        
        lecture = self.db.get_lecture("lec1")
        self.assertIsNone(lecture)
    
    def test_add_lecture_to_student(self):
        """Test adding lecture to student"""
        self.db.add_student(123, "user", "пн 15:00")
        self.db.add_lecture("lec1", "Основы", "basics.pdf", "/path/basics.pdf")
        
        result = self.db.add_lecture_to_student(123, "lec1")
        self.assertTrue(result)
        
        student = self.db.get_student(123)
        self.assertIn("lec1", student['lectures'])
    
    def test_remove_lecture_from_student(self):
        """Test removing lecture from student"""
        self.db.add_student(123, "user", "пн 15:00")
        self.db.add_lecture("lec1", "Основы", "basics.pdf", "/path/basics.pdf")
        self.db.add_lecture_to_student(123, "lec1")
        
        result = self.db.remove_lecture_from_student(123, "lec1")
        self.assertTrue(result)
        
        student = self.db.get_student(123)
        self.assertNotIn("lec1", student['lectures'])
    
    def test_get_stats(self):
        """Test getting database statistics"""
        self.db.add_student(123, "user1", "пн 15:00")
        self.db.add_student(456, "user2", "вт 17:00")
        self.db.add_lecture("lec1", "Основы", "basics.pdf", "/path/basics.pdf")
        
        stats = self.db.get_stats()
        self.assertEqual(stats['students'], 2)
        self.assertEqual(stats['lectures'], 1)
        self.assertGreater(stats['total_keys'], 0)
    
    def test_student_lecture_workflow(self):
        """Test complete workflow: add student, add lecture, assign lecture"""
        # Add student
        self.db.add_student(123, "vasya", "пн,ср,пт 15:00-16:00")
        
        # Add lectures
        self.db.add_lecture("lec1", "Периодическая таблица", "table.pdf", "/lectures/table.pdf")
        self.db.add_lecture("lec2", "Химические связи", "bonds.pdf", "/lectures/bonds.pdf")
        
        # Assign lectures to student
        self.db.add_lecture_to_student(123, "lec1")
        self.db.add_lecture_to_student(123, "lec2")
        
        # Verify student has lectures
        student = self.db.get_student(123)
        self.assertEqual(len(student['lectures']), 2)
        
        # Remove one lecture
        self.db.remove_lecture_from_student(123, "lec1")
        student = self.db.get_student(123)
        self.assertEqual(len(student['lectures']), 1)
        self.assertIn("lec2", student['lectures'])


class TestBotConfiguration(unittest.TestCase):
    """Test bot configuration"""
    
    def test_config_file_exists(self):
        """Test that config file exists and is valid JSON"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            # Check required fields
            self.assertIn('bot_token', config)
            self.assertIn('admin_ids', config)
            self.assertIn('redis', config)
            self.assertIn('lectures_storage', config)
        except FileNotFoundError:
            self.fail("config.json not found")
        except json.JSONDecodeError:
            self.fail("config.json is not valid JSON")
    
    def test_admin_ids_is_list(self):
        """Test that admin_ids is a list"""
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        self.assertIsInstance(config['admin_ids'], list)


class TestDataValidation(unittest.TestCase):
    """Test data validation"""
    
    def setUp(self):
        """Set up test database"""
        self.db = DatabaseManager()
        self.db.clear_all_data()
    
    def tearDown(self):
        """Clean up"""
        self.db.clear_all_data()
    
    def test_invalid_user_id_type(self):
        """Test adding student with invalid user ID"""
        # Should handle string user_id
        result = self.db.add_student("123", "user", "пн 15:00")
        self.assertTrue(result)
    
    def test_empty_schedule(self):
        """Test adding student with empty schedule"""
        result = self.db.add_student(123, "user", "")
        self.assertTrue(result)
        
        student = self.db.get_student(123)
        self.assertEqual(student['schedule'], "")
    
    def test_special_characters_in_username(self):
        """Test username with special characters"""
        result = self.db.add_student(123, "user_123-test", "пн 15:00")
        self.assertTrue(result)
        
        student = self.db.get_student(123)
        self.assertEqual(student['username'], "user_123-test")


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDatabaseManager))
    suite.addTests(loader.loadTestsFromTestCase(TestBotConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestDataValidation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
