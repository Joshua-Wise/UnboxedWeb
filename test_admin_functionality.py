#!/usr/bin/env python3
"""Test script to verify admin functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Set up test database path
os.environ['DB_PATH'] = '/tmp/test_users.db'

from app.users import (
    init_db, create_user, get_all_users,
    delete_user, update_user_password, toggle_admin_status,
    User, authenticate_user
)

def test_admin_functionality():
    """Test admin user management functionality"""

    print("=" * 60)
    print("Testing Admin User Management Functionality")
    print("=" * 60)

    # Clean up any existing test database
    test_db_path = '/tmp/test_users.db'
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print("✓ Cleaned up existing test database")

    # Test 1: Initialize database
    print("\n1. Testing database initialization...")
    try:
        init_db()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

    # Test 2: Verify default users
    print("\n2. Testing default users...")
    admin_user = User.get_by_username('admin')
    regular_user = User.get_by_username('user')

    if admin_user and admin_user.is_admin:
        print(f"✓ Admin user exists with admin privileges")
    else:
        print(f"✗ Admin user not created or missing admin privileges")
        return False

    if regular_user and not regular_user.is_admin:
        print(f"✓ Regular user exists without admin privileges")
    else:
        print(f"✗ Regular user not created or has incorrect privileges")
        return False

    # Test 3: Authenticate users
    print("\n3. Testing authentication...")
    auth_admin = authenticate_user('admin', 'admin123')
    auth_user = authenticate_user('user', 'user123')

    if auth_admin and auth_admin.is_admin:
        print(f"✓ Admin authentication successful")
    else:
        print(f"✗ Admin authentication failed")
        return False

    if auth_user and not auth_user.is_admin:
        print(f"✓ Regular user authentication successful")
    else:
        print(f"✗ Regular user authentication failed")
        return False

    # Test 4: Create new user
    print("\n4. Testing user creation...")
    success, message = create_user('testuser', 'password123', is_admin=False)

    if success:
        print(f"✓ User creation successful: {message}")
        new_user = User.get_by_username('testuser')
        if new_user and not new_user.is_admin:
            print(f"✓ New user exists with correct privileges")
        else:
            print(f"✗ New user not found or has incorrect privileges")
            return False
    else:
        print(f"✗ User creation failed: {message}")
        return False

    # Test 5: Get all users
    print("\n5. Testing get all users...")
    users = get_all_users()

    if len(users) == 3:  # admin, user, testuser
        print(f"✓ Retrieved all {len(users)} users")
        for user in users:
            role = "Admin" if user['is_admin'] else "User"
            print(f"   - {user['username']} ({role})")
    else:
        print(f"✗ Expected 3 users, got {len(users)}")
        return False

    # Test 6: Update user password
    print("\n6. Testing password update...")
    test_user = User.get_by_username('testuser')
    success, message = update_user_password(test_user.id, 'newpassword456')

    if success:
        print(f"✓ Password update successful: {message}")
        # Verify new password works
        auth_test = authenticate_user('testuser', 'newpassword456')
        if auth_test:
            print(f"✓ New password authentication successful")
        else:
            print(f"✗ New password authentication failed")
            return False
    else:
        print(f"✗ Password update failed: {message}")
        return False

    # Test 7: Toggle admin status
    print("\n7. Testing toggle admin status...")
    success, message = toggle_admin_status(test_user.id)

    if success:
        print(f"✓ Admin status toggled: {message}")
        updated_user = User.get(test_user.id)
        if updated_user.is_admin:
            print(f"✓ User is now an admin")
        else:
            print(f"✗ User admin status not updated")
            return False
    else:
        print(f"✗ Toggle admin status failed: {message}")
        return False

    # Test 8: Prevent deleting last admin
    print("\n8. Testing last admin protection...")
    success, message = delete_user(admin_user.id)

    if not success and "last admin" in message.lower():
        print(f"✓ Protected last admin from deletion: {message}")
    else:
        print(f"✗ Last admin protection failed")
        return False

    # Test 9: Delete user
    print("\n9. Testing user deletion...")
    success, message = delete_user(regular_user.id)

    if success:
        print(f"✓ User deletion successful: {message}")
        deleted_user = User.get(regular_user.id)
        if not deleted_user:
            print(f"✓ User successfully removed from database")
        else:
            print(f"✗ User still exists in database")
            return False
    else:
        print(f"✗ User deletion failed: {message}")
        return False

    # Test 10: Verify final user count
    print("\n10. Testing final user count...")
    final_users = get_all_users()

    if len(final_users) == 2:  # admin and testuser (now admin)
        print(f"✓ Final user count correct: {len(final_users)} users")
        admin_count = sum(1 for u in final_users if u['is_admin'])
        if admin_count == 2:
            print(f"✓ Correct number of admins: {admin_count}")
        else:
            print(f"✗ Expected 2 admins, got {admin_count}")
            return False
    else:
        print(f"✗ Expected 2 users, got {len(final_users)}")
        return False

    print("\n" + "=" * 60)
    print("All tests passed successfully!")
    print("=" * 60)

    # Clean up test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print("\n✓ Test database cleaned up")

    return True

if __name__ == '__main__':
    try:
        success = test_admin_functionality()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
