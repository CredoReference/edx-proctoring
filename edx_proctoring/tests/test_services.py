# pylint: disable=unused-argument

"""
Test for the xBlock service
"""

from __future__ import absolute_import

from datetime import datetime, timedelta
import types
import unittest
import pytz

from edx_proctoring.services import (
    ProctoringService
)
from edx_proctoring.exceptions import UserNotFoundException
from edx_proctoring import api as edx_proctoring_api


class MockCreditService(object):
    """
    Simple mock of the Credit Service
    """

    def __init__(self, enrollment_mode='verified', profile_fullname='Wolfgang von Strucker',
                 course_name='edx demo', student_email='foo@bar'):
        """
        Initializer
        """
        self.order = 0
        self.status = {
            'course_name': course_name,
            'enrollment_mode': enrollment_mode,
            'profile_fullname': profile_fullname,
            'student_email': student_email,
            'credit_requirement_status': []
        }

    def get_credit_state(self, user_id, course_key, return_course_info=False):  # pylint: disable=unused-argument
        """
        Mock implementation
        """
        return self.status

    # pylint: disable=unused-argument
    def set_credit_requirement_status(self, user_id, course_key_or_id, req_namespace,
                                      req_name, status="satisfied", reason=None):
        """
        Mock implementation
        """

        found = [
            requirement
            for requirement in self.status['credit_requirement_status']
            if requirement['name'] == req_name and
            requirement['namespace'] == req_namespace and
            requirement['course_id'] == unicode(course_key_or_id)
        ]

        if not found:
            self.status['credit_requirement_status'].append({
                'course_id': unicode(course_key_or_id),
                'req_namespace': req_namespace,
                'namespace': req_namespace,
                'name': req_name,
                'status': status,
                'order': self.order,
            })
        else:
            found[0]['status'] = status

        self.order = self.order + 1

    # pylint: disable=unused-argument
    # pylint: disable=invalid-name
    def remove_credit_requirement_status(self, user_id, course_key_or_id, req_namespace, req_name):
        """
        Mock implementation for removing the credit requirement status.
        """

        for requirement in self.status['credit_requirement_status']:
            match = (
                requirement['name'] == req_name and
                requirement['namespace'] == req_namespace and
                requirement['course_id'] == unicode(course_key_or_id)
            )
            if match:
                self.status['credit_requirement_status'].remove(requirement)
                break

        return True


class MockCreditServiceWithCourseEndDate(MockCreditService):
    """
    mock of the Credit Service but overrides get_credit_state to return a past course_end_date
    """

    def get_credit_state(self, user_id, course_key, return_course_info=False):  # pylint: disable=unused-argument
        """
        Mock implementation
        """
        self.status['course_end_date'] = datetime.now(pytz.UTC) + timedelta(days=-1)
        return self.status


class MockCreditServiceNone(MockCreditService):
    """
    Mock Credit Service that returns None for the credit state every time.
    """

    def get_credit_state(self, user_id, course_key, return_course_info=False):  # pylint: disable=unused-argument
        """
        Mock implementation
        """
        return None


class MockInstructorService(object):
    """
    Simple mock of the Instructor Service
    """
    def __init__(self, is_user_course_staff=True):
        """
        Initializer
        """
        self.is_user_course_staff = is_user_course_staff

    # pylint: disable=unused-argument
    def delete_student_attempt(self, student_identifier, course_id, content_id, requesting_user):
        """
        Mock implementation
        """
        # Ensure that this method was called with a real user object
        if not hasattr(requesting_user, 'id'):
            raise UserNotFoundException
        return True

    def is_course_staff(self, user, course_id):
        """
        Mocked implementation of is_course_staff
        """
        return self.is_user_course_staff

    def send_support_notification(self, course_id, exam_name, student_username, review_status):
        """
        Mocked implementation of send_support_notification
        """
        pass


class TestProctoringService(unittest.TestCase):
    """
    Tests for ProctoringService
    """
    def test_basic(self):
        """
        See if the ProctoringService exposes the expected methods
        """

        service = ProctoringService()

        for attr_name in dir(edx_proctoring_api):
            attr = getattr(edx_proctoring_api, attr_name, None)
            if isinstance(attr, types.FunctionType) and not attr_name.startswith('_'):
                self.assertTrue(hasattr(service, attr_name))

    def test_singleton(self):
        """
        Test to make sure the ProctoringService is a singleton.
        """
        service1 = ProctoringService()
        service2 = ProctoringService()
        self.assertIs(service1, service2)


class MockGrade(object):
    """Fake PersistentSubsectionGrade instance."""
    def __init__(self, earned_all=0.0, earned_graded=0.0):
        self.earned_all = earned_all
        self.earned_graded = earned_graded


class MockGradeOverride(object):
    """Fake PersistentSubsectionGradeOverride instance."""
    def __init__(self, earned_all=0.0, earned_graded=0.0):
        self.earned_all_override = earned_all
        self.earned_graded_override = earned_graded


class MockGradesService(object):
    """
    Simple mock of the Grades Service
    """
    def __init__(self):
        """Initialize empty data stores for grades and overrides (just dicts)"""
        self.grades = {}
        self.overrides = {}

    def init_grade(self, user_id, course_key_or_id, usage_key_or_id, earned_all, earned_graded):
        """Initialize a grade in MockGradesService for testing. Actual GradesService does not have this method."""
        self.grades[str(user_id) + str(course_key_or_id) + str(usage_key_or_id)] = MockGrade(
            earned_all=earned_all,
            earned_graded=earned_graded
        )

    def get_subsection_grade(self, user_id, course_key_or_id, usage_key_or_id):
        """Returns entered grade for key (user_id + course_key + subsection) or None"""
        key = str(user_id) + str(course_key_or_id) + str(usage_key_or_id)
        if key in self.overrides:
            # pretend override was applied
            return MockGrade(
                earned_all=self.overrides[key].earned_all_override,
                earned_graded=self.overrides[key].earned_graded_override
            )
        return self.grades.get(str(user_id) + str(course_key_or_id) + str(usage_key_or_id))

    def get_subsection_grade_override(self, user_id, course_key_or_id, usage_key_or_id):
        """Returns entered grade override for key (user_id + course_key + subsection) or None"""
        return self.overrides.get(str(user_id) + str(course_key_or_id) + str(usage_key_or_id))

    def override_subsection_grade(self, user_id, course_key_or_id, usage_key_or_id, earned_all=None,
                                  earned_graded=None):
        """Sets grade override earned points for key (user_id + course_key + subsection)"""
        key = str(user_id) + str(course_key_or_id) + str(usage_key_or_id)
        self.overrides[key] = MockGradeOverride(
            earned_all=earned_all,
            earned_graded=earned_graded
        )

    def undo_override_subsection_grade(self, user_id, course_key_or_id, usage_key_or_id):
        """Deletes grade override for key (user_id + course_key + subsection)"""
        key = str(user_id) + str(course_key_or_id) + str(usage_key_or_id)
        if key in self.overrides:
            del self.overrides[key]
