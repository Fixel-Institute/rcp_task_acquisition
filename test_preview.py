from pathlib import Path
import sys

# Ensure the package src is importable when running from the repository root
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

try:
	import wx
	from rcp_task_acquisition.panels.DelsysPreview import DelsysPreview
except Exception as e:
	print("Failed to import dependencies:", e)
	raise


def main():
	app = wx.App(False)
	frame = DelsysPreview(None, title="Delsys Preview Test")
	frame.Show()
	app.MainLoop()


if __name__ == "__main__":
	main()

