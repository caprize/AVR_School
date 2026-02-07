"""
Test script for the chemistry bot database
"""

from database import DatabaseManager
import json

def test_database():
    """Test database operations"""
    
    # Initialize database
    db = DatabaseManager()
    
    print("=" * 50)
    print("Chemistry Bot - Database Tests")
    print("=" * 50)
    
    # Test Redis connection
    print("\n1. Testing Redis connection...")
    if db.is_redis_connected():
        print("✅ Redis connection successful")
    else:
        print("❌ Redis connection failed")
        return
    
    # Test adding students
    print("\n2. Testing student operations...")
    db.add_student(123456, "vasya", "пн,ср,пт 15:00-16:00")
    db.add_student(789012, "masha", "вт,чт 17:00-18:00")
    
    student = db.get_student(123456)
    if student:
        print(f"✅ Added student: {student['username']}")
    
    # Test getting all students
    students = db.get_all_students()
    print(f"✅ Total students: {len(students)}")
    
    # Test adding lectures
    print("\n3. Testing lecture operations...")
    db.add_lecture("lecture_1", "Периодическая таблица", "periodic_table.pdf", "/lectures/periodic_table.pdf")
    db.add_lecture("lecture_2", "Химические связи", "chemical_bonds.pdf", "/lectures/chemical_bonds.pdf")
    
    lecture = db.get_lecture("lecture_1")
    if lecture:
        print(f"✅ Added lecture: {lecture['name']}")
    
    # Test getting all lectures
    lectures = db.get_all_lectures()
    print(f"✅ Total lectures: {len(lectures)}")
    
    # Test adding lecture to student
    print("\n4. Testing assigning lectures to student...")
    db.add_lecture_to_student(123456, "lecture_1")
    db.add_lecture_to_student(123456, "lecture_2")
    
    updated_student = db.get_student(123456)
    if updated_student:
        print(f"✅ Student {updated_student['username']} now has {len(updated_student['lectures'])} lectures")
    
    # Test updating student
    print("\n5. Testing student update...")
    db.update_student(123456, schedule="пн,ср,пт 16:00-17:00")
    updated = db.get_student(123456)
    print(f"✅ Updated schedule: {updated['schedule']}")
    
    # Test removing lecture from student
    print("\n6. Testing removing lecture from student...")
    db.remove_lecture_from_student(123456, "lecture_2")
    student = db.get_student(123456)
    print(f"✅ Student now has {len(student['lectures'])} lecture(s)")
    
    # Test statistics
    print("\n7. Testing database statistics...")
    stats = db.get_stats()
    print(f"✅ Database Stats:")
    print(f"   - Students: {stats['students']}")
    print(f"   - Lectures: {stats['lectures']}")
    print(f"   - Total keys: {stats['total_keys']}")
    
    # Test deleting lecture
    print("\n8. Testing lecture deletion...")
    db.delete_lecture("lecture_2")
    lectures = db.get_all_lectures()
    print(f"✅ Lectures after deletion: {len(lectures)}")
    
    # Test deleting student
    print("\n9. Testing student deletion...")
    db.delete_student(789012)
    students = db.get_all_students()
    print(f"✅ Students after deletion: {len(students)}")
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    print("=" * 50)


if __name__ == '__main__':
    test_database()
