from src.runtime.app_runtime import clear_previous_data


def test_clear_previous_data_keeps_main_log_backup(tmp_path):
    logs_dir = tmp_path / "logs"
    reports_dir = tmp_path / "reports"
    logs_dir.mkdir()
    reports_dir.mkdir()

    main_log = logs_dir / "main.log"
    old_report = reports_dir / "old.json"
    temp_file = tmp_path / "scratch.tmp"
    main_log.write_text("previous log", encoding="utf-8")
    old_report.write_text("{}", encoding="utf-8")
    temp_file.write_text("temp", encoding="utf-8")

    clear_previous_data(project_root=tmp_path)

    assert (logs_dir / "main_backup.log").read_text(encoding="utf-8") == "previous log"
    assert not main_log.exists()
    assert not old_report.exists()
    assert not temp_file.exists()
    assert reports_dir.exists()
