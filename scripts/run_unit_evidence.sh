#!/usr/bin/env bash
set -euo pipefail

mkdir -p evidence/unit

PYTHON_BIN="${PYTHON_BIN:-/Users/prithivirajsah/Desktop/Hamrocarrental_backend/.venv/bin/python}"

TESTS=(
  "UT-01 tests/test_password_validation.py::test_get_password_hash_and_verify_round_trip"
  "UT-02 tests/test_password_validation.py::test_get_password_hash_raises_for_bcrypt_overflow"
  "UT-03 tests/test_password_validation.py::test_validate_password_strength_reports_weak_patterns"
  "UT-04 tests/test_password_validation.py::test_verify_password_returns_false_for_invalid_hash_input"
  "UT-05 tests/test_user_schemas.py::test_user_create_accepts_valid_payload"
  "UT-06 tests/test_user_schemas.py::test_user_create_rejects_weak_password"
  "UT-07 tests/test_user_schemas.py::test_user_create_rejects_password_mismatch"
  "UT-08 tests/test_user_schemas.py::test_user_profile_update_normalizes_optional_text"
  "UT-09 tests/test_user_schemas.py::test_reset_password_request_rejects_blank_token"
  "UT-10 tests/test_auth_jwt.py::test_create_access_token_contains_subject_claim"
  "UT-11 tests/test_auth_jwt.py::test_authenticate_user_returns_none_when_user_not_found"
  "UT-12 tests/test_auth_jwt.py::test_authenticate_user_validates_bcrypt_password"
  "UT-13 tests/test_auth_jwt.py::test_authenticate_user_migrates_plaintext_password"
  "UT-14 tests/test_auth_jwt.py::test_authenticate_user_rejects_wrong_plaintext_password"
  "UT-15 tests/test_auth_jwt.py::test_is_admin_user_allows_admin_role_in_production"
  "UT-16 tests/test_auth_jwt.py::test_is_admin_user_denies_regular_user_in_production"
  "UT-17 tests/test_auth_jwt.py::test_is_admin_user_allows_regular_role_in_dev"
  "UT-18 tests/test_user_crud.py::test_create_user_hashes_password_and_lowercases_email"
  "UT-19 tests/test_user_crud.py::test_get_user_by_email_is_case_insensitive"
  "UT-20 tests/test_user_crud.py::test_update_user_role_raises_for_unknown_user"
  "UT-21 tests/test_user_crud.py::test_update_user_profile_persists_changes"
  "UT-22 tests/test_user_crud.py::test_count_users_by_role_returns_correct_counts"
  "UT-23 tests/test_booking_core_logic.py::test_create_booking_sets_pending_status"
  "UT-24 tests/test_booking_core_logic.py::test_has_booking_overlap_detects_conflicts"
  "UT-25 tests/test_booking_core_logic.py::test_has_booking_overlap_with_other_users_ignores_same_user"
  "UT-26 tests/test_booking_core_logic.py::test_get_bookings_count_by_user_tracks_status_totals"
)

FAILED=0

for entry in "${TESTS[@]}"; do
  CASE_ID="${entry%% *}"
  TEST_TARGET="${entry#* }"
  LOG_FILE="evidence/unit/${CASE_ID}.log"

  echo "Running ${CASE_ID} -> ${TEST_TARGET}"
  if "${PYTHON_BIN}" -m pytest -v "${TEST_TARGET}" | tee "${LOG_FILE}"; then
    echo "${CASE_ID} PASSED"
  else
    echo "${CASE_ID} FAILED"
    FAILED=1
  fi
  echo "----------------------------------------"
done

if [[ ${FAILED} -ne 0 ]]; then
  echo "One or more unit tests failed. Check evidence/unit/*.log"
  exit 1
fi

echo "All unit evidence logs generated in evidence/unit"
