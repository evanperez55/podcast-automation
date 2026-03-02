"""Tests for retry_utils module."""

import pytest
from unittest.mock import patch
from retry_utils import retry_with_backoff


class TestRetryWithBackoff:
    def test_success_no_retry(self):
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_retries_then_succeeds(self):
        call_count = 0

        @retry_with_backoff(
            max_retries=3, base_delay=0.01, retryable_exceptions=(ValueError,)
        )
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary")
            return "ok"

        assert fail_twice() == "ok"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        @retry_with_backoff(
            max_retries=2, base_delay=0.01, retryable_exceptions=(ValueError,)
        )
        def always_fail():
            raise ValueError("permanent")

        with pytest.raises(ValueError, match="permanent"):
            always_fail()

    def test_non_retryable_exception_raises_immediately(self):
        call_count = 0

        @retry_with_backoff(
            max_retries=3, base_delay=0.01, retryable_exceptions=(ValueError,)
        )
        def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            raise_type_error()
        assert call_count == 1

    @patch("retry_utils.time.sleep")
    def test_exponential_delay(self, mock_sleep):
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=1.0,
            backoff_factor=2.0,
            retryable_exceptions=(ValueError,),
        )
        def fail_all():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            fail_all()

        delays = [call[0][0] for call in mock_sleep.call_args_list]
        assert delays[0] == pytest.approx(1.0)
        assert delays[1] == pytest.approx(2.0)
        assert delays[2] == pytest.approx(4.0)
