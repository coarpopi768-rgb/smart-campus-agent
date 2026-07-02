"""
Tests: RBAC Permissions & Data Scope
Validates that each role has correct permissions and data scoping.
"""
import sys
sys.path.insert(0, '.')
from auth.auth import check_permission, get_data_scope, PERMISSIONS, DATA_SCOPE


def test_admin_has_all_permissions():
    """Admin should have all permissions."""
    for action in PERMISSIONS["admin"]:
        assert check_permission("admin", action), f"Admin missing permission: {action}"


def test_teacher_permissions():
    """Teacher: can query DB, send email, view students. Cannot manage users or view analytics."""
    assert check_permission("teacher", "db_query") == True
    assert check_permission("teacher", "score_query") == True
    assert check_permission("teacher", "send_email") == True
    assert check_permission("teacher", "rag_query") == True
    assert check_permission("teacher", "view_all_students") == True
    assert check_permission("teacher", "manage_users") == False
    assert check_permission("teacher", "view_analytics") == False


def test_student_permissions():
    """Student: can query DB and RAG. Cannot send email, manage users, view all students."""
    assert check_permission("student", "db_query") == True
    assert check_permission("student", "score_query") == True
    assert check_permission("student", "rag_query") == True
    assert check_permission("student", "search") == True
    assert check_permission("student", "send_email") == False
    assert check_permission("student", "manage_users") == False
    assert check_permission("student", "view_all_students") == False


def test_guest_permissions():
    """Guest: only RAG and search. Everything else blocked."""
    assert check_permission("guest", "rag_query") == True
    assert check_permission("guest", "search") == True
    assert check_permission("guest", "db_query") == False
    assert check_permission("guest", "score_query") == False
    assert check_permission("guest", "send_email") == False
    assert check_permission("guest", "student_info") == False


def test_unknown_role_falls_back_to_guest():
    """Unknown role should get guest permissions."""
    assert check_permission("hacker", "db_query") == False
    assert check_permission("hacker", "rag_query") == True


def test_data_scope_levels():
    """Data scope should map correctly."""
    assert get_data_scope("admin") == "all"
    assert get_data_scope("teacher") == "department"
    assert get_data_scope("student") == "self"
    assert get_data_scope("guest") == "none"
    assert get_data_scope("unknown") == "none"


def test_student_cannot_email():
    """Critical: student must not be able to send emails."""
    assert not check_permission("student", "send_email"), "STUDENT SHOULD NOT SEND EMAIL"


def test_guest_cannot_access_db():
    """Critical: guest must not access database."""
    assert not check_permission("guest", "db_query"), "GUEST SHOULD NOT ACCESS DB"


if __name__ == "__main__":
    all_tests = [f for f in dir() if f.startswith('test_')]
    passed = 0
    failed = 0
    for test_name in all_tests:
        try:
            globals()[test_name]()
            print(f"  PASS  {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {test_name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(all_tests)}")
    sys.exit(1 if failed else 0)
