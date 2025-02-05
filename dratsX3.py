#!/usr/bin/env python3

import re
import time
import curses 
import random
from curses import wrapper

from gpiozero import Button
from picamera2 import Picamera2
from datetime import datetime
from signal import pause
import cv2
import os
import numpy as np
import subprocess # added m"

button = Button(23)   # GPIO 23 is intialized as 'button'
camera = Picamera2()  # the connected camera is intialized as 'camera'
camera.start()
haar_cascade_path = '/home/pi1/Downloads/haarcascade_frontalface_default.xml'

if not os.path.exists(haar_cascade_path):
	print("Haar Cascade XML file not found at the specified location.")
else:
	face_cascade = cv2.CascadeClassifier(haar_cascade_path)

def detect_face(image):
    # Use OpenCV Haar Cascade for face detection
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image_gray = cv2.equalizeHist(image_gray)
    faces = face_cascade.detectMultiScale(image_gray, scaleFactor=1.05, minNeighbors=4, 
        minSize=(30, 30))
    return faces

def show_image(file_path):  # Added this function
    try:
        print(f'Showing image: {file_path}')
        subprocess.run(["feh", file_path], check=True)  # Using subprocess to open feh
    except subprocess.CalledProcessError as e:  # Adding exception handling
        print(f"Failed to open image with feh: {e}") 
        
def add_frame(background, choice): #takes in openCV image (of picture taken)
	#add alpha channel to picture
	background = cv2.cvtColor(background, cv2.COLOR_BGR2BGRA) # the flip
	background[:, :, 3] = 255 # 255
	#*#*# CHANGE ME *#*#*#
	if 'Expression' in choice:
		foreground = cv2.imread("/home/pi1/Pink_NewFrame.png", cv2.IMREAD_UNCHANGED) 
	elif 'Scientific' in choice:
		foreground = cv2.imread("/home/pi1/Green_NewFrame.png", cv2.IMREAD_UNCHANGED)
	elif 'Justic' in choice:
		foreground = cv2.imread("/home/pi1/Blue_NewFrame.png", cv2.IMREAD_UNCHANGED) 
	
	# normalize alpha channels from 0-255 to 0-1
	alpha_background = background[:,:,3] / 255.0
	alpha_foreground = foreground[:,:,3] / 255.0
	# set adjusted colors
	for color in range(0, 3):
		background[:,:,color] = alpha_foreground * foreground[:,:,color] + \
			alpha_background * background[:,:,color] * (1 - alpha_foreground)
			
	# set adjusted alpha and denormalize back to 0-255
	background[:,:,3] = (1 - (1 - alpha_foreground) * (1 - alpha_background)) * 255
	return background
            
def smooth(image, faces):
    mask = np.zeros_like(image)
    for (x, y, w, h) in faces:
        # Create a mask with an elliptical region
        center = (x + w // 2, y + h // 2)  # Center of the face
        axes = (w // 2, h // 2)  # Axes for the ellipse
        cv2.ellipse(mask, center, axes, 0, 0, 360, (255, 255, 255), -1)  # Draw the ellipse on the mask
    
    # Smooth the face region with the mask
    face_region = cv2.bitwise_and(image, mask)  # Apply the mask to the image
    return face_region

def detect_face(image):
    # Use OpenCV Haar Cascade for face detection
    image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    image_gray = cv2.equalizeHist(image_gray)
    faces = face_cascade.detectMultiScale(image_gray, scaleFactor=1.05, minNeighbors=4, 
        minSize=(30, 30))
    return faces

def process_image(file_path, choice):
    #cartoonize
    image = cv2.imread(file_path) 
    faces = detect_face(image)
    face = smooth(image, faces)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) 
    gray = cv2.medianBlur(gray, 5)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY, 9, 9)
    color = cv2.bilateralFilter(image, 9, 250, 250)
    
    cartoon_background = cv2.bitwise_and(color, color, mask=edges)
    # Now blend the face with the cartoonized background, keeping face details intact
    final_image = cv2.addWeighted(cartoon_background, 1, face, 1, 0)
    final_image = cv2.convertScaleAbs(cartoon_background, alpha=1.2, beta=20)  

    top, bottom, left, right = 280, 200, 0, 0  
    padded_cartoon = cv2.copyMakeBorder(final_image, top, bottom, left, right, 
                                        cv2.BORDER_CONSTANT, value=[255, 0, 0])  

    #add frame
    final = add_frame(padded_cartoon, choice)
    final_file_path = file_path.replace('photos', 'photos_cartoon').replace('.jpg', 'cart.jpg')
    cv2.imwrite(final_file_path, final)
    return final_file_path
    
def capture(student_info):
	name = student_info[0]
	r1 = 'Y' if 'Y' in student_info[1] else 'N'
	r2 = 'Y' if 'Y' in student_info[2] else 'N'
	uniq = student_info[3]
	file_path = f'/home/pi1/photos/{uniq}_{name}_{r1}_{r2}_.jpg' # save path defined
	camera.capture_file(file_path) # capture_file, a picamera2 function
	return file_path
 
def on_button_pressed(win, student_info):
    # Print the countdown in the window
    choice = student_info[4]
    for i in range(3, 0, -1):
        win.clear()  
        win.attron(curses.color_pair(4))
        ## hand-keyed centering, as win_height,win_width not returned from main
        win.addstr(6, 28, f"{i}",curses.color_pair(1))  # Print the countdown number at the center of the window        
        win.border()
        win.refresh()  # Refresh to show the update
        time.sleep(1)
        
    file_path = capture(student_info)
    processed_img_path = process_image(file_path, choice)
    show_image(processed_img_path)

def spool_text(win, text, colr_pr, disp_row, delay=0.1):
	""" spool_text prints characters to the screen one at a time """
	height, width = win.getmaxyx()
	start_col = max(2, width//2 -len(text)//2)
	for idx, char in enumerate(text):
		if 0 <= start_col + idx < width-1:
			win.addch(disp_row, start_col + idx, char, curses.color_pair(colr_pr)) ## !! keyed centering !!
		win.refresh()
		time.sleep(delay)

def draw_menu(win, current_row_idx, menu_items):
	""" posts prompt and sets color_pairs for higlighted and non-higlighted text """
	win.clear()
	height, width = win.getmaxyx()
	up_arrow = u'\u2191'
	down_arrow = u'\u2193'
	win.addstr(2,1,f"How will you use your superpower? ({up_arrow}{down_arrow})", curses.color_pair(2))
	for idx, row in enumerate(menu_items):
		x = max(2, width//2-len(row)//2)
		y = height // 2 - len(menu_items) // 2 + idx
		if idx == current_row_idx:  ## current row is highligted
			win.attron(curses.color_pair(3))  # Using a different colorpair for highlighting
			win.addstr(y, x, row)
			win.attroff(curses.color_pair(3))
		else:
			win.attron(curses.color_pair(2))
			win.addstr(y, x, row)
			win.attroff(curses.color_pair(2))
	win.attron(curses.color_pair(4)) 
	win.box()
	win.attroff(curses.color_pair(4)) 
	win.refresh()

def draw_yes_no_menu(win, current_choice_idx, choices):
	""" Draws a horizontal A/B menu with highlight """
	height, width = win.getmaxyx()
	menu_y = height - 5   #$#$#$#$#$#$#$#$ hand-keyed, FIVE lines from bottom
	for idx, choice in enumerate(choices):
		x = width // 2 - len(" ".join(choices)) // 2 + (len(choice) + 4) * idx  # center horizontally
		if idx == current_choice_idx:
			win.attron(curses.color_pair(3))  # Highlight current selection
			win.addstr(menu_y, x, choice)
			win.attroff(curses.color_pair(3))
		else:
			win.attron(curses.color_pair(2))
			win.addstr(menu_y, x, choice)
			win.attroff(curses.color_pair(2))
	win.refresh()

def handle_yes_no_response(win):
	""" Function to handle yes/no response """
	choices = ["Yes(Y)", "No(N)"]
	current_choice_idx = 0
	draw_yes_no_menu(win, current_choice_idx, choices)

	while True:
		curses.noecho()
		key = win.getch()
		if key == (94 and 91 and 91 and 68) or key in [59,121]: 
			current_choice_idx = (current_choice_idx - 1) % len(choices)
		elif key ==  (94 and 91 and 91 and 67) or key in [78,110]: 
			current_choice_idx = (current_choice_idx + 1) % len(choices)
		elif key == curses.KEY_ENTER or key in [10, 13]:
			return choices[current_choice_idx]
			  
		draw_yes_no_menu(win, current_choice_idx, choices) 
		
def start_screen(stdscr):
	curses.curs_set(0)
	stdscr.clear()
	time_delay = 0.01
	# Initialize colors
	curses.start_color()
	curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
	curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
	curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Using for menu highlight
	curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)


	# Get terminal window height and width
	height, width = stdscr.getmaxyx()

	# Create dimension of new window, and find center
	win_height, win_width = 14, 55
	max_text_width=win_width-2
	win = curses.newwin(win_height, win_width, height // 2 - win_height // 2, width // 2 - win_width // 2)
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4)) 

   	
	## Welcome and collect user name
	## Prompt user for input
	prompt1 = "Welcome the PCAS SuperHero PiBooth!!"
	prompt2 = "Press Enter to Start"
	spool_text(win, prompt1, 2, 3, time_delay)
	win.addstr(8, win_width//2 - len(prompt2)//2 , prompt2, curses.A_BLINK)
	win.refresh()
	key = win.getch()
	while key != curses.KEY_ENTER and key != 10:
		key = win.getch()
		
def matrix(stdscr):
	"""this is the matrix screen intro"""
	time_delay = 0.01
	curses.curs_set(0) # hide the cursor
	height, width = stdscr.getmaxyx()
	
	curses.start_color()
	curses.init_pair(2,curses.COLOR_GREEN, curses.COLOR_BLACK)
	
	# create a list to store
	column_positions = [random.randint(-20,0) for _ in range(width)]

	
	stdscr.nodelay(True)
	stdscr.timeout(50)
	
	while True:
		for x in range(width):
			y = column_positions[x]
			if y < height-1:
				char = chr(random.randint(33,126)) # random printable character
				if 0 <= y < height and 0 <= x < width:
					stdscr.addch(y,x,char,curses.color_pair(2) | curses.A_NORMAL)
					if any(y >= height-1 for y in column_positions):
						stdscr.addch(y,x,char,curses.color_pair(2) | curses.A_DIM)
					
				# increment the Y position ofthe column
				column_positions[x] += 1
			else:	
				# Reset the column position to a random starting point
				column_positions[x] = random.randint(-20,0)
		stdscr.refresh()
		
		# Check for key press to exit
		if all(y >= height-1 for y in column_positions):
			column_positions = [random.randint(-20,0) for _ in range(width)]
			stdscr.clear()
		if stdscr.getch() != -1:
			break # exit the loop if any key pressed
			
		time.sleep(0.05)
 
def main(stdscr):
	curses.curs_set(0)
	stdscr.clear()
	time_delay = 0.01
	# Initialize colors
	curses.start_color()
	curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
	curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
	curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Using for menu highlight
	curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)


	# Get terminal window height and width
	height, width = stdscr.getmaxyx()

	# Create dimension of new window, and find center
	win_height, win_width = 14, 55
	max_text_width=win_width-2
	win = curses.newwin(win_height, win_width, height // 2 - win_height // 2, width // 2 - win_width // 2)
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4)) 

   	
	## Welcome and collect user name
	## Prompt user for input
	prompt1 = "Welcome to the PCAS SuperHero PiBooth!"

	spool_text(win, prompt1, 2, 3, time_delay)
	time.sleep(.75)
	win.clear()
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4)) 
	prompt2 = "What is your first name?... "
	spool_text(win, prompt2, 2, 3, time_delay)
    
	curses.echo()
	name = win.getstr(5, win_width//2-4, 20).decode('utf-8')

	# Display the entered name
	win.clear()
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4)) 
	
	prompt3 = f"Hello {name}"
	spool_text(win,prompt3,2,2,time_delay)
	time.sleep(.25)
	
	prompt4 = f"We'll use your email address to email your photo"
	spool_text(win,prompt4,2,4,time_delay)
	time.sleep(.25)
	
	prompt5 = f"Do you have your M-Card in your posession?"
	spool_text(win,prompt5,2,6,time_delay)  
	
	back_arrow = u'\u2190'
	forward_arrow = u'\u2192'
	prompt5 = f"use {back_arrow} and {forward_arrow} or Y and N"
	spool_text(win, prompt5, 2, 11, time_delay)
	prompt6 = f"press ENTER to accept the highlighted option"
	spool_text(win, prompt6, 2, 12, time_delay)
	## "handle_yes_no_response" calls "draw_yes_no_menu"
	reply1 = handle_yes_no_response(win)
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4))
	win.refresh()

	
	## can't return value (choices[current_choice_idx]) as written, 
	## using keyed reply1 instead as inputMeth variable if-elsed below
	if reply1 == "Yes(Y)":
		win.move(10,1)
		win.clrtoeol()
		win.attron(curses.color_pair(4))
		win.border()
		win.move(11,1)
		win.clrtoeol()
		win.move(12,1) 
		win.clrtoeol()
		win.box()
		win.addstr(11, win_width//2-len('You chose yes, press any key')//2, "You chose YES, press any key", curses.color_pair(2))
		
	elif reply1 == "No(N)":
		win.move(10,1)
		win.clrtoeol()
		win.attron(curses.color_pair(4))
		win.border()
		win.move(11,1)
		win.clrtoeol()
		win.move(12,1) 
		win.clrtoeol()
		win.box()
		win.addstr(11, win_width//2-len('You chose no, press any key')//2, "You chose No, press any key", curses.color_pair(2))
		
 
	win.getch()
	win.clear()
	
	win.attron(curses.color_pair(4))
	win.border() 
	win.refresh()
	curses.noecho()
	
	while True:
		card_data = [] 
		win.clear()
		win.attron(curses.color_pair(4))
		win.border()
		# win.attroff(curses.color_pair(4)) 
		txt0 =  f"Swipe your M-Card, please...\n"
		win.move(1,1)
		win.clrtoeol()
		win.addstr(1, win_width//2 - len(txt0)//2, txt0, curses.color_pair(3) | curses.A_BLINK)
		win.box()
		win.refresh()
        
		while True:
			ch = win.getch()
			if ch == ord('\n'):
				break
			else:
				card_data.append(chr(ch))
				win.attron(curses.color_pair(2))
				win.box()
				win.addch('*')
				win.box()
        
		card_data_str = ''.join(card_data)
		pattern = r"\d+([A-Za-z]{1,8})\?"
		match = re.search(pattern, card_data_str)

		if match:
			extracted_string = match.group(1)
			txt1 = f"Extracted String: {extracted_string.lower()}@umich.edu"
			uniq = extracted_string.lower()
			win.box()
			win.addstr(7, win_width//2 - len(txt1)//2, txt1, curses.color_pair(3))
			txt2 = "***** MUTANT VERIFIED *****"
			time.sleep(2)
			

			spool_text(win,txt2,3,9,.1)
			txt0 =  f"Press Any Key\n"
			win.move(1,1)
			win.clrtoeol()
			win.box()
			win.addstr(1,1,"                                       ") # blank out 
			win.addstr(1, win_width//2 - len(txt0)//2, txt0, curses.color_pair(3) | curses.A_BLINK)
			
			break  # Exit loop if successful swipe
		else:
			txt = "Badswipe. Try Again."
			win.box()
			win.addstr(8, win_width//2 - len(txt)//2 , txt, curses.A_BLINK)
			win.refresh()
			time.sleep(2)
			# Clear the card data feedback area for the next try
			win.move(8, 2)
			win.clrtoeol()
			win.move(9, 2)
			win.clrtoeol()
	win.getch()
	win.clear()
	win.attron(curses.color_pair(4))
	win.box() 
	win.addstr(1,win_width//2-len("FYI: Card Data Received:")//2,"FYI: Card Data Received:", curses.color_pair(2))
	win.attron(curses.color_pair(2))
	win.addstr(3,2, card_data_str)	
	win.addstr(5,win_width//2-len("This will not be shown, only unique name taken")//2,"This will not be shown, only unique name taken")
	win.attron(curses.color_pair(4))	
	win.box()
	win.refresh()		
	win.getch()
	
	win.clear()
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4)) 


	prompt7 = "Thanks for the information!!"
	spool_text(win, prompt7, 2, 2, time_delay)
	prompt8 = "May we use your photograph for"
	spool_text(win, prompt8, 2, 4, time_delay)
	prompt9 = "PCAS web and promotions?"
	spool_text(win, prompt9, 2, 5, time_delay)
	
	prompt10 = f"use {back_arrow} and {forward_arrow} or Y and N"
	spool_text(win, prompt10, 2, 11, time_delay)
	prompt11 = f"press ENTER to accept the highlighted option"
	spool_text(win, prompt11, 2, 12, time_delay)
	
	## "handle_yes_no_response" calls "draw_yes_no_menu"6
	reply2 = handle_yes_no_response(win)
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4))
	win.refresh()
	
	if reply2 == "Yes(Y)":
		win.move(10,1)
		win.clrtoeol()
		win.attron(curses.color_pair(4))
		win.border()
		win.move(11,1)
		win.clrtoeol()
		win.move(12,1) 
		win.clrtoeol()
		win.box()
		win.addstr(11, win_width//2-len('You chose yes, press any key')//2, "You chose YES, press any key", curses.color_pair(2))

	elif reply2 == "No(N)":
		win.move(10,1)
		win.clrtoeol()
		win.attron(curses.color_pair(4))
		win.border()
		win.move(11,1)
		win.clrtoeol()
		win.move(12,1) 
		win.clrtoeol() 
		win.box()
		win.addstr(11, win_width//2-len('You chose no, press any key')//2, "You chose NO, press any key", curses.color_pair(2))


	win.getch()
	win.clear()

	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4)) 

	prompt12 = f"Lastly, may we add you to our email lists"
	spool_text(win,prompt12,2,2,time_delay)
	time.sleep(.25)

	prompt13 = f"For information about course and events"
	spool_text(win,prompt13,2,4,time_delay)
	time.sleep(.25)
	
	prompt14 = f"regarding computing in LSA?"
	spool_text(win,prompt14,2,5,time_delay)
	time.sleep(.25)
	
	prompt15 = f"use {back_arrow} and {forward_arrow} or Y and N"
	spool_text(win, prompt15, 2, 11, time_delay)
	prompt16 = f"press ENTER to accept the highlighted option"
	spool_text(win, prompt16, 2, 12, time_delay)
	
	
	## "handle_yes_no_response" calls "draw_yes_no_menu"
	reply3 = handle_yes_no_response(win)
	win.attron(curses.color_pair(4))
	win.border()
	win.attroff(curses.color_pair(4))
	win.refresh()
	
	if reply3 == "Yes(Y)":
		win.move(10,1)
		win.clrtoeol()
		win.attron(curses.color_pair(4))
		win.border()
		win.move(11,1)
		win.clrtoeol()
		win.move(12,1) 
		win.clrtoeol()
		win.box()
		win.addstr(11, win_width//2-len('You chose yes, press any key')//2, "You chose YES, press any key", curses.color_pair(2))
	
	elif reply3 == "No(N)":
		win.move(10,1)
		win.clrtoeol()
		win.attron(curses.color_pair(4))
		win.border()
		win.move(11,1)
		win.clrtoeol()
		win.move(12,1) 
		win.clrtoeol()
		win.box()
		win.addstr(11, win_width//2-len('You chose no, press any key')//2, "You chose NO, press any key", curses.color_pair(2))
	
	win.getch()
	
    # Menu items
	menu_items = ['Computing for Expression', 'Computing for Scientific Discovery', 'Computing for Justice']
	current_row_idx = 0
	print(len(menu_items))

	draw_menu(win, current_row_idx, menu_items)
	curses.noecho()
	
	while True:
		key = win.getch()
		if key == (94 and 91 and 91 and 65):
			up_arrow = u'\u2191'
			current_row_idx = (current_row_idx - 1) % len(menu_items)
			draw_menu(win, current_row_idx, menu_items)
			win.addstr(2,1,"                                        ")
			win.addstr(2,2,f"up arrow pressed {up_arrow}",curses.color_pair(2))
			win.refresh()
		elif key == (94 and 91 and 91 and 66):
			down_arrow = u'\u2193'
			current_row_idx = (current_row_idx + 1) % len(menu_items)
			draw_menu(win, current_row_idx, menu_items)
			win.addstr(2,1,"                                        ")
			win.addstr(2,2,f"down arrow pressed {down_arrow}",curses.color_pair(2))
			win.refresh()
		elif key == (94 and 91 and 91 and 68): 
			back_arrow = u'\u2190'
			current_row_idx = (current_row_idx - 1) % len(menu_items)
			draw_menu(win, current_row_idx, menu_items)
			win.addstr(2,2,"                                       ")
			win.addstr(2,2,f"back arrow pressed {back_arrow}",curses.color_pair(2))
		elif key == (94 and 91 and 91 and 67): 
			forward_arrow = u'\u2192'
			current_row_idx = (current_row_idx + 1) % len(menu_items)
			draw_menu(win, current_row_idx, menu_items)
			win.addstr(2,2,"                                       ")
			win.addstr(2,2,f"forward arrow pressed {forward_arrow}",curses.color_pair(2))	
		elif key == curses.KEY_ENTER or key in [10, 13]:
			# Enter key to select
			selected_item = f"'{menu_items[current_row_idx]}'"
			x = win.getmaxyx()[1]//2 - len(selected_item)//2
			win.addstr(9,x,selected_item,curses.color_pair(1) | curses.A_BLINK)
			win.refresh()
			time.sleep(1)
			win.addstr(11, win_width // 2 - len(f"Alright, {name}, Press Button When Ready") // 2,
						   f"Alright, {name}, Press Key When Ready", curses.color_pair(2))			
			win.refresh()
			student_info = [name, reply1, reply2, uniq, selected_item]
			win.getch()
			button.when_pressed = on_button_pressed(win, student_info)
			break

if __name__ == "__main__":
	try: 
		while True:
			curses.wrapper(start_screen)
			curses.wrapper(matrix)
			wrapper(main)
	except KeyboardInterrupt:
		print('exiting')
		button.close()
		camera.close()
			

