import tkinter as tk

root = tk.Tk()
root.title("Take a break!")
root.geometry("700x500")

label = tk.Label(root, text="Get up and stretch!")
label.pack(padx=20, pady=20)

instruction = tk.Label(root, text="How many minutes until the next break?")
instruction.pack(pady=10)

time_entry = tk.Entry(root)
time_entry.pack()

start_button = tk.Button(root, text="Start Timer")
start_button.pack(pady=20)

root.mainloop()
