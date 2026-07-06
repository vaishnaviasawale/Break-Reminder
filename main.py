import tkinter as tk

def disable_inputs():
    time_entry.config(state="disabled")
    start_button.config(state="disabled")

def enable_inputs():
    time_entry.config(state="normal")
    start_button.config(state="normal")


def timer_finished():
    print("Time for a break!")
    root.deiconify() # Make the window visible again
    enable_inputs()

def start_timer():
    minutes_text = time_entry.get()

    try:
        minutes = int(minutes_text)
        if minutes <= 0:
            print("Not a valid number of minutes!")
            return

        print(f"Starting timer for {minutes} minutes")
        disable_inputs()
        root.withdraw() # Hide the window, but keep the program running
        milliseconds = 5000
        root.after(milliseconds, timer_finished)
        
    except ValueError as e:
        # Value error because usually strings can be converted into ints
        # but this particular string does not represent an integer aka the value is invalid
        # If it was something like int([1, 2, 3]) it would be a TypeError as 
        # Python does not even know how to convert it into an int
        print("Please enter a number! Error: ", e)
        # Do I need to return here? No, because Python has reached the end of the function and
        # returns automatically here (the function ends immediately after this Except block)

root = tk.Tk()
root.title("Take a break!")
root.geometry("700x500")

label = tk.Label(root, text="Get up and stretch!")
label.pack(padx=20, pady=20)

instruction = tk.Label(root, text="How many minutes until the next break?")
instruction.pack(pady=10)

time_entry = tk.Entry(root)
time_entry.pack()

start_button = tk.Button(root, text="Start Timer", command=start_timer)
start_button.pack(pady=20)

root.mainloop()
