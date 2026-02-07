"""
Database utilities for managing students and lectures
"""

import redis
import json
from typing import Dict, List, Optional
from datetime import datetime


class DatabaseManager:
    """Manage Redis database operations"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        """Initialize Redis connection"""
        self.r = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
        # Initialize default category
        self._init_default_category()
    
    def _init_default_category(self) -> None:
        """Initialize the default 'Без категории' category"""
        try:
            if not self.r.sismember("categories", "Без категории"):
                self.r.sadd("categories", "Без категории")
                self.r.hset("category_lectures", "Без категории", json.dumps([]))
        except Exception as e:
            print(f"Error initializing default category: {e}")
    
    # Student operations
    def add_student(self, user_id: int, username: str, schedule: str) -> bool:
        """Add new student to database"""
        try:
            student_data = {
                'user_id': user_id,
                'username': username,
                'schedule': schedule,
                'lectures': [],
                'created_at': datetime.now().isoformat()
            }
            self.r.set(f"student:{user_id}", json.dumps(student_data))
            return True
        except Exception as e:
            print(f"Error adding student: {e}")
            return False
    
    def get_student(self, user_id: int) -> Optional[Dict]:
        """Get student data by user ID"""
        try:
            data = self.r.get(f"student:{user_id}")
            return json.loads(data) if data else None
        except Exception as e:
            print(f"Error getting student: {e}")
            return None
    
    def update_student(self, user_id: int, **kwargs) -> bool:
        """Update student data"""
        try:
            student = self.get_student(user_id)
            if not student:
                return False
            
            student.update(kwargs)
            self.r.set(f"student:{user_id}", json.dumps(student))
            return True
        except Exception as e:
            print(f"Error updating student: {e}")
            return False
    
    def get_all_students(self) -> List[Dict]:
        """Get all students from database"""
        try:
            students = []
            for key in self.r.keys("student:*"):
                data = self.r.get(key)
                if data:
                    students.append(json.loads(data))
            return students
        except Exception as e:
            print(f"Error getting students: {e}")
            return []
    
    def delete_student(self, user_id: int) -> bool:
        """Delete student from database"""
        try:
            self.r.delete(f"student:{user_id}")
            return True
        except Exception as e:
            print(f"Error deleting student: {e}")
            return False
    
    def add_lecture_to_student(self, user_id: int, lecture_id: str) -> bool:
        """Add lecture to student's available lectures"""
        try:
            student = self.get_student(user_id)
            if not student:
                return False
            
            if lecture_id not in student['lectures']:
                student['lectures'].append(lecture_id)
                self.r.set(f"student:{user_id}", json.dumps(student))
            return True
        except Exception as e:
            print(f"Error adding lecture to student: {e}")
            return False
    
    def remove_lecture_from_student(self, user_id: int, lecture_id: str) -> bool:
        """Remove lecture from student's available lectures"""
        try:
            student = self.get_student(user_id)
            if not student:
                return False
            
            if lecture_id in student['lectures']:
                student['lectures'].remove(lecture_id)
                self.r.set(f"student:{user_id}", json.dumps(student))
            return True
        except Exception as e:
            print(f"Error removing lecture from student: {e}")
            return False
    
    # Category operations
    def add_category(self, category_name: str) -> bool:
        """Add new lecture category"""
        try:
            if not self.r.sismember("categories", category_name):
                self.r.sadd("categories", category_name)
                self.r.hset("category_lectures", category_name, json.dumps([]))
            return True
        except Exception as e:
            print(f"Error adding category: {e}")
            return False
    
    def get_all_categories(self) -> List[str]:
        """Get all lecture categories"""
        try:
            categories = list(self.r.smembers("categories"))
            if "Без категории" not in categories:
                categories.append("Без категории")
            return sorted(categories)
        except Exception as e:
            print(f"Error getting categories: {e}")
            return ["Без категории"]
    
    def delete_category(self, category_name: str) -> bool:
        """Delete category and move its lectures to 'Без категории'"""
        try:
            if category_name == "Без категории":
                return False
            
            # Get lectures from this category
            lectures_data = self.r.hget("category_lectures", category_name)
            lectures = json.loads(lectures_data) if lectures_data else []
            
            # Move lectures to "Без категории"
            uncategorized_data = self.r.hget("category_lectures", "Без категории")
            uncategorized = json.loads(uncategorized_data) if uncategorized_data else []
            uncategorized.extend(lectures)
            self.r.hset("category_lectures", "Без категории", json.dumps(uncategorized))
            
            # Delete category
            self.r.srem("categories", category_name)
            self.r.hdel("category_lectures", category_name)
            return True
        except Exception as e:
            print(f"Error deleting category: {e}")
            return False
    
    # Lecture operations
    def add_lecture(self, lecture_id: str, name: str, filename: str, filepath: str, category: str = "Без категории") -> bool:
        """Add new lecture to database"""
        try:
            if not category:
                category = "Без категории"
            
            # Ensure category exists
            self.add_category(category)
            
            # Store lecture metadata
            lecture_info = {
                'id': lecture_id,
                'name': name,
                'category': category
            }
            self.r.set(f"lecture:{lecture_id}", json.dumps(lecture_info))
            
            # Store file info
            file_info = {
                'filename': filename,
                'filepath': filepath,
                'created_at': datetime.now().isoformat()
            }
            self.r.set(f"{lecture_id}:file", json.dumps(file_info))
            
            # Add to category
            lectures_data = self.r.hget("category_lectures", category)
            lectures = json.loads(lectures_data) if lectures_data else []
            if lecture_id not in lectures:
                lectures.append(lecture_id)
                self.r.hset("category_lectures", category, json.dumps(lectures))
            
            return True
        except Exception as e:
            print(f"Error adding lecture: {e}")
            return False
    
    def get_lecture(self, lecture_id: str) -> Optional[Dict]:
        """Get lecture data by ID"""
        try:
            lecture_data = self.r.get(f"lecture:{lecture_id}")
            if not lecture_data:
                return None
            
            lecture = json.loads(lecture_data)
            file_data = self.r.get(f"{lecture_id}:file")
            file_info = json.loads(file_data) if file_data else {}
            
            return {
                'id': lecture_id,
                'name': lecture['name'],
                'category': lecture.get('category', 'Без категории'),
                'file': file_info
            }
        except Exception as e:
            print(f"Error getting lecture: {e}")
            return None
    
    def get_lectures_by_category(self, category: str) -> Dict[str, str]:
        """Get all lectures in a category (id -> name)"""
        try:
            lectures_data = self.r.hget("category_lectures", category)
            lectures_list = json.loads(lectures_data) if lectures_data else []
            
            result = {}
            for lecture_id in lectures_list:
                lecture = self.get_lecture(lecture_id)
                if lecture:
                    result[lecture_id] = lecture['name']
            
            return result
        except Exception as e:
            print(f"Error getting lectures by category: {e}")
            return {}
    
    def get_all_lectures_by_category(self) -> Dict[str, Dict[str, str]]:
        """Get all lectures organized by category"""
        try:
            result = {}
            for category in self.get_all_categories():
                result[category] = self.get_lectures_by_category(category)
            return result
        except Exception as e:
            print(f"Error getting all lectures by category: {e}")
            return {}
    
    def get_all_lectures(self) -> Dict[str, str]:
        """Get all lectures (id -> name) - legacy support"""
        try:
            all_lectures = {}
            categories = self.get_all_categories()
            for category in categories:
                lectures = self.get_lectures_by_category(category)
                all_lectures.update(lectures)
            return all_lectures
        except Exception as e:
            print(f"Error getting lectures: {e}")
            return {}
    
    def delete_lecture(self, lecture_id: str) -> bool:
        """Delete lecture from database and remove from all students"""
        try:
            # Get lecture info to find its category
            lecture = self.get_lecture(lecture_id)
            if not lecture:
                return False
            
            category = lecture.get('category', 'Без категории')
            
            # Remove from category
            lectures_data = self.r.hget("category_lectures", category)
            lectures = json.loads(lectures_data) if lectures_data else []
            if lecture_id in lectures:
                lectures.remove(lecture_id)
                self.r.hset("category_lectures", category, json.dumps(lectures))
            
            # Remove lecture from all students
            students = self.get_all_students()
            for student in students:
                if lecture_id in student['lectures']:
                    student['lectures'].remove(lecture_id)
                    self.r.set(f"student:{student['user_id']}", json.dumps(student))
            
            # Delete lecture
            self.r.delete(f"lecture:{lecture_id}")
            self.r.delete(f"{lecture_id}:file")
            return True
        except Exception as e:
            print(f"Error deleting lecture: {e}")
            return False
    
    def move_lecture_to_category(self, lecture_id: str, new_category: str) -> bool:
        """Move lecture to a different category"""
        try:
            lecture = self.get_lecture(lecture_id)
            if not lecture:
                return False
            
            old_category = lecture.get('category', 'Без категории')
            
            if old_category == new_category:
                return True
            
            # Ensure new category exists
            self.add_category(new_category)
            
            # Remove from old category
            if old_category:
                lectures_data = self.r.hget("category_lectures", old_category)
                lectures = json.loads(lectures_data) if lectures_data else []
                if lecture_id in lectures:
                    lectures.remove(lecture_id)
                    self.r.hset("category_lectures", old_category, json.dumps(lectures))
            
            # Add to new category
            lectures_data = self.r.hget("category_lectures", new_category)
            lectures = json.loads(lectures_data) if lectures_data else []
            if lecture_id not in lectures:
                lectures.append(lecture_id)
                self.r.hset("category_lectures", new_category, json.dumps(lectures))
            
            # Update lecture info
            lecture['category'] = new_category
            self.r.set(f"lecture:{lecture_id}", json.dumps(lecture))
            
            return True
        except Exception as e:
            print(f"Error moving lecture: {e}")
            return False
    
    def update_lecture(self, lecture_id: str, name: str) -> bool:
        """Update lecture name"""
        try:
            if self.r.hexists("lectures", lecture_id):
                self.r.hset("lectures", lecture_id, name)
                return True
            return False
        except Exception as e:
            print(f"Error updating lecture: {e}")
            return False
    
    # Utility operations
    def is_redis_connected(self) -> bool:
        """Check if Redis is connected"""
        try:
            self.r.ping()
            return True
        except:
            return False
    
    def clear_all_data(self) -> bool:
        """Clear all data from database (use with caution)"""
        try:
            self.r.flushdb()
            return True
        except Exception as e:
            print(f"Error clearing database: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            students_count = len(self.r.keys("student:*"))
            lectures_count = self.r.hlen("lectures")
            
            return {
                'students': students_count,
                'lectures': lectures_count,
                'total_keys': self.r.dbsize()
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def cleanup_orphaned_lectures(self) -> int:
        """Remove lectures from students that no longer exist in the system"""
        try:
            all_lectures = self.get_all_lectures()
            students = self.get_all_students()
            removed_count = 0
            
            for student in students:
                original_count = len(student.get('lectures', []))
                student['lectures'] = [
                    lec_id for lec_id in student.get('lectures', [])
                    if lec_id in all_lectures
                ]
                
                if len(student['lectures']) < original_count:
                    removed_count += original_count - len(student['lectures'])
                    self.r.set(f"student:{student['user_id']}", json.dumps(student))
            
            return removed_count
        except Exception as e:
            print(f"Error cleaning up orphaned lectures: {e}")
            return 0
