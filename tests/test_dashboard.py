from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_dashboard_renders_without_exceptions():
    app = AppTest.from_file(Path(__file__).parents[1] / "dashboard.py")

    app.run(timeout=15)

    assert not app.exception
    assert app.title[0].value == "Retail Operations Dashboard"
    assert len(app.metric) == 6
