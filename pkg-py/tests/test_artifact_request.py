from querychat._shiny_module import artifact_action_for_status


def test_running_or_initial_status_waits():
    assert artifact_action_for_status("running") == "wait"
    assert artifact_action_for_status("initial") == "wait"


def test_success_opens():
    assert artifact_action_for_status("success") == "open"


def test_error_or_cancelled_drops():
    assert artifact_action_for_status("error") == "drop"
    assert artifact_action_for_status("cancelled") == "drop"
