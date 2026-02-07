"""
Admin CLI tool for managing the bot database
"""

import json
import sys
from database import DatabaseManager
from datetime import datetime


def print_menu():
    """Print main menu"""
    print("\n" + "=" * 50)
    print("Chemistry Bot - Admin CLI")
    print("=" * 50)
    print("1. Add student")
    print("2. View student")
    print("3. List all students")
    print("4. Update student schedule")
    print("5. Add lecture to student")
    print("6. Remove lecture from student")
    print("7. Add lecture")
    print("8. View lecture")
    print("9. List all lectures")
    print("10. Delete lecture")
    print("11. Delete student")
    print("12. Database statistics")
    print("13. Clear all data")
    print("0. Exit")
    print("=" * 50)


def add_student(db):
    """Add a new student"""
    user_id = int(input("Enter student user ID: "))
    username = input("Enter student username: ")
    schedule = input("Enter student schedule (e.g., 'пн,ср,пт 15:00-16:00'): ")
    
    if db.add_student(user_id, username, schedule):
        print(f"✅ Student '{username}' added successfully!")
    else:
        print("❌ Error adding student")


def view_student(db):
    """View student details"""
    user_id = int(input("Enter student user ID: "))
    student = db.get_student(user_id)
    
    if student:
        print("\n" + "-" * 40)
        print(f"User ID: {student['user_id']}")
        print(f"Username: {student['username']}")
        print(f"Schedule: {student['schedule']}")
        print(f"Available lectures: {len(student['lectures'])}")
        if student['lectures']:
            for lecture_id in student['lectures']:
                lecture = db.get_lecture(lecture_id)
                if lecture:
                    print(f"  - {lecture['name']}")
        print(f"Created at: {student.get('created_at', 'N/A')}")
        print("-" * 40)
    else:
        print("❌ Student not found")


def list_students(db):
    """List all students"""
    students = db.get_all_students()
    
    if not students:
        print("📭 No students found")
        return
    
    print("\n" + "-" * 60)
    print(f"{'ID':<15} {'Username':<15} {'Schedule':<20} {'Lectures':<10}")
    print("-" * 60)
    
    for student in students:
        print(f"{student['user_id']:<15} {student['username']:<15} {student['schedule']:<20} {len(student['lectures']):<10}")
    
    print("-" * 60)


def update_student_schedule(db):
    """Update student schedule"""
    user_id = int(input("Enter student user ID: "))
    new_schedule = input("Enter new schedule: ")
    
    if db.update_student(user_id, schedule=new_schedule):
        print("✅ Schedule updated!")
    else:
        print("❌ Error updating schedule")


def add_lecture_to_student(db):
    """Add lecture to student"""
    user_id = int(input("Enter student user ID: "))
    
    lectures = db.get_all_lectures()
    if not lectures:
        print("❌ No lectures available")
        return
    
    print("\nAvailable lectures:")
    lecture_list = list(lectures.items())
    for i, (lecture_id, lecture_name) in enumerate(lecture_list, 1):
        print(f"  {i}. {lecture_name} (ID: {lecture_id})")
    
    choice = int(input("Enter lecture number: "))
    if 1 <= choice <= len(lecture_list):
        lecture_id = lecture_list[choice - 1][0]
        if db.add_lecture_to_student(user_id, lecture_id):
            print("✅ Lecture added to student!")
        else:
            print("❌ Error adding lecture")
    else:
        print("❌ Invalid choice")


def add_lecture(db):
    """Add a new lecture"""
    name = input("Enter lecture name: ")
    filename = input("Enter filename (e.g., 'lecture.pdf'): ")
    filepath = input("Enter file path: ")
    
    lecture_id = f"lecture_{int(datetime.now().timestamp())}"
    
    if db.add_lecture(lecture_id, name, filename, filepath):
        print(f"✅ Lecture '{name}' added successfully!")
        print(f"   Lecture ID: {lecture_id}")
    else:
        print("❌ Error adding lecture")


def view_lecture(db):
    """View lecture details"""
    lectures = db.get_all_lectures()
    
    if not lectures:
        print("❌ No lectures found")
        return
    
    print("\nAvailable lectures:")
    lecture_list = list(lectures.items())
    for i, (lecture_id, lecture_name) in enumerate(lecture_list, 1):
        print(f"  {i}. {lecture_name}")
    
    choice = int(input("Enter lecture number: "))
    if 1 <= choice <= len(lecture_list):
        lecture_id = lecture_list[choice - 1][0]
        lecture = db.get_lecture(lecture_id)
        
        if lecture:
            print("\n" + "-" * 40)
            print(f"ID: {lecture['id']}")
            print(f"Name: {lecture['name']}")
            print(f"Filename: {lecture['file'].get('filename', 'N/A')}")
            print(f"Path: {lecture['file'].get('filepath', 'N/A')}")
            print(f"Created: {lecture['file'].get('created_at', 'N/A')}")
            print("-" * 40)
    else:
        print("❌ Invalid choice")


def list_lectures(db):
    """List all lectures"""
    lectures = db.get_all_lectures()
    
    if not lectures:
        print("📭 No lectures found")
        return
    
    print("\n" + "-" * 50)
    print(f"{'#':<5} {'Name':<30} {'ID':<15}")
    print("-" * 50)
    
    for i, (lecture_id, lecture_name) in enumerate(lectures.items(), 1):
        print(f"{i:<5} {lecture_name:<30} {lecture_id:<15}")
    
    print("-" * 50)


def delete_lecture(db):
    """Delete a lecture"""
    lectures = db.get_all_lectures()
    
    if not lectures:
        print("❌ No lectures found")
        return
    
    list_lectures(db)
    
    choice = int(input("Enter lecture number to delete: "))
    lecture_list = list(lectures.items())
    
    if 1 <= choice <= len(lecture_list):
        lecture_id = lecture_list[choice - 1][0]
        lecture_name = lecture_list[choice - 1][1]
        
        confirm = input(f"Are you sure you want to delete '{lecture_name}'? (yes/no): ")
        if confirm.lower() == 'yes':
            if db.delete_lecture(lecture_id):
                print("✅ Lecture deleted!")
            else:
                print("❌ Error deleting lecture")
        else:
            print("❌ Deletion cancelled")
    else:
        print("❌ Invalid choice")


def delete_student(db):
    """Delete a student"""
    list_students(db)
    
    user_id = int(input("Enter student user ID to delete: "))
    student = db.get_student(user_id)
    
    if student:
        confirm = input(f"Are you sure you want to delete '{student['username']}'? (yes/no): ")
        if confirm.lower() == 'yes':
            if db.delete_student(user_id):
                print("✅ Student deleted!")
            else:
                print("❌ Error deleting student")
        else:
            print("❌ Deletion cancelled")
    else:
        print("❌ Student not found")


def show_statistics(db):
    """Show database statistics"""
    stats = db.get_stats()
    
    print("\n" + "-" * 40)
    print("📊 Database Statistics")
    print("-" * 40)
    print(f"Total students: {stats.get('students', 0)}")
    print(f"Total lectures: {stats.get('lectures', 0)}")
    print(f"Total database keys: {stats.get('total_keys', 0)}")
    print("-" * 40)


def clear_all_data(db):
    """Clear all data (CAUTION!)"""
    print("\n⚠️  WARNING: This will delete ALL data!")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm == 'DELETE ALL':
        if db.clear_all_data():
            print("✅ All data cleared!")
        else:
            print("❌ Error clearing data")
    else:
        print("❌ Operation cancelled")


def main():
    """Main CLI loop"""
    db = DatabaseManager()
    
    # Check Redis connection
    if not db.is_redis_connected():
        print("❌ Error: Cannot connect to Redis!")
        print("Please make sure Redis is running.")
        sys.exit(1)
    
    print("✅ Connected to Redis")
    
    while True:
        print_menu()
        choice = input("Enter your choice: ").strip()
        
        try:
            if choice == '0':
                print("👋 Goodbye!")
                break
            elif choice == '1':
                add_student(db)
            elif choice == '2':
                view_student(db)
            elif choice == '3':
                list_students(db)
            elif choice == '4':
                update_student_schedule(db)
            elif choice == '5':
                add_lecture_to_student(db)
            elif choice == '6':
                user_id = int(input("Enter student user ID: "))
                list_lectures(db)
                lecture_id = input("Enter lecture ID: ")
                if db.remove_lecture_from_student(user_id, lecture_id):
                    print("✅ Lecture removed from student!")
                else:
                    print("❌ Error removing lecture")
            elif choice == '7':
                add_lecture(db)
            elif choice == '8':
                view_lecture(db)
            elif choice == '9':
                list_lectures(db)
            elif choice == '10':
                delete_lecture(db)
            elif choice == '11':
                delete_student(db)
            elif choice == '12':
                show_statistics(db)
            elif choice == '13':
                clear_all_data(db)
            else:
                print("❌ Invalid choice, please try again")
        
        except ValueError:
            print("❌ Invalid input, please try again")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()
