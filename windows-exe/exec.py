import tkinter as tk

def button_click():
    label.config(text=f"Hello, {entry.get()}!")


root = tk.Tk()
root.title("Simple GUI")

label = tk.Label(root, text="Enter your name:")
label.pack()

entry = tk.Entry(root)
entry.pack(pady = 5)

button = tk.Button(root, text="Greet", command=button_click)
button.pack(pady = 10)

root.mainloop()