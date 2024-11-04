import tkinter as tk
from ui import MigrationTool

def main():
    root = tk.Tk()
    app = MigrationTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()
