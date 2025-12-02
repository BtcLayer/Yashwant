import os
import tempfile

from scripts.check_heartbeat import find_heartbeat_files, main


def test_find_heartbeat_files(tmp_path):
    base = tmp_path / "paper_trading_outputs" / "logs" / "botA" / "stream1"
    base.mkdir(parents=True)
    hb = base / "heartbeat.json"
    hb.write_text('{"alive": true}')

    found = find_heartbeat_files(str(tmp_path / "paper_trading_outputs" / "logs"))
    assert len(found) >= 1
    assert any(str(hb) in p for p in found)


def test_main_no_files(tmp_path, monkeypatch):
    # run main against an empty location and expect a non-zero exit
    root = str(tmp_path / "logs")
    os.makedirs(root, exist_ok=True)

    # emulate CLI
    monkeypatch.setattr("sys.argv", ["check_heartbeat.py", root])
    rc = main()
    assert rc == 2
