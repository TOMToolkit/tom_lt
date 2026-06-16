from django.test import tag, TestCase


@tag('canary')
class TestAPPCanary(TestCase):
    """NOTE: To run these tests in your venv: python ./{{tom_app}}/tests/run_tests.py"""

    def test_canary(self):
        """Test something that hit live services."""
        pass
