# http://remotescripts.blogspot.com
"""
8*8 Step Sequencer for launchpad

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

based on APC stepsquencer by by Hanz Petrov, itslef based on  
LiveControl Sequencer module by ST8 <http://monome.q3f.org>
and the CS Step Sequencer Live API example by Cycling '74 <http://www.cycling74.com>
"""

import Live
from consts import *
from _Framework.ControlSurfaceComponent import ControlSurfaceComponent
from _Framework.ButtonElement import ButtonElement
from _Framework.EncoderElement import EncoderElement
from _Framework.SessionComponent import SessionComponent
from _Framework.ButtonMatrixElement import ButtonMatrixElement

INITIAL_SCROLLING_DELAY = 4
INTERVAL_SCROLLING_DELAY = 1

QUANTIZATION_MAP = [1,0.5,0.25,0.125]#1/4 1/8 1/16 1/32
QUANTIZATION_COLOR_MAP = [LED_OFF,AMBER_THIRD,AMBER_HALF,AMBER_FULL]

VELOCITY_MAP = [70,90,110]
VELOCITY_COLOR_MAP = [GREEN_THIRD,GREEN_HALF,GREEN_FULL]
VELOCITY_COLOR_HIGHLIGHT_MAP = [RED_THIRD,RED_HALF,RED_FULL]
STEPSEQ_MODE_NORMAL=1
STEPSEQ_MODE_LANE_MUTE=2

class StepSequencerComponent(ControlSurfaceComponent):
	__module__ = __name__
	__doc__ = ' Generic Step Sequencer Component '

	def __init__(self, parent, matrix,side_buttons,nav_buttons):
		ControlSurfaceComponent.__init__(self)
		self._is_active = False
		self._parent = parent
		#buttons
		self._matrix = matrix
		self._width = self._matrix.width()
		self._height = self._matrix.height()

		self._buttons = None
		self._nav_up_button = None
		self._nav_down_button = None
		self._nav_left_button = None
		self._nav_right_button = None 
		self._loop_length_inc_button = None
		self._loop_length_dec_button = None
		self._velocity_button = None
		self._quantization_button = None
		self._follow_button = None
		self._lock_button = None
		self._fold_button = None
		self._velocity_shift_button = None
		self._mute_shift_button = None
		self._lane_mute_buttons = None
		self._muted_lanes = []
		self._mode = 1
		
		#values
		self._quantization_index = 2
		self._quantization = QUANTIZATION_MAP[self._quantization_index]
		self._velocity_index = 2
		self._velocity = VELOCITY_MAP[self._velocity_index]
		self._is_fold = False
		self._is_locked = False
		self._is_following = False
		self._is_velocity_shifted = False
		self._is_mute_shifted = False	

		self._loop_start_index = 0
		self._loop_end_index = 7
		self._loop_index_length = 0
		self._loop_length = None
		self._loop_start = None
		self._loop_end = None

		#fill the cache
		self._grid_buffer = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0], [0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
		self._grid_back_buffer = [[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0], [0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]]
		
		#notes
		self._bank_index = 0 #bank index;
		self._key_indexes=[0,0,0,0,0,0,0,0]
		self._key_indexes[0] = 36 #C1 Note
		self._compute_key_indexes(True)#init note lanes
		self._sequencer_clip = None
		self._clip_notes = []
		self._force_update = True

		#set buttons
		self.set_loop_length_dec_button(side_buttons[0])
		self.set_loop_length_inc_button(side_buttons[1])
		self.set_quantization_button(side_buttons[2])
		self.set_velocity_button(side_buttons[3])
		#self.set_follow_button(side_buttons[4])
		self.set_lock_button(side_buttons[4])
		self.set_fold_button(side_buttons[5])
		self.set_velocity_shift_button(side_buttons[6])
		self.set_mute_shift_button(side_buttons[7])
		self.set_button_matrix(matrix)
		self.set_lane_mute_buttons(side_buttons)
		self.set_nav_buttons(nav_buttons[0],nav_buttons[1],nav_buttons[2],nav_buttons[3])

		#scrolls
		self._scroll_up_ticks_delay = -1
		self._scroll_down_ticks_delay = -1
		self._scroll_right_ticks_delay = -1
		self._scroll_left_ticks_delay = -1
		self._register_timer_callback(self._on_timer)
		
	#def set_is_active(self,is_active):
	#	self.is_active=is_active
	
	#def clear_buffer(self):
	#	for x in range(self._width-1):
	#		self._grid_buffer[x] = []
	#		self._grid_back_buffer[x] = []
	#		for y in range(self._width-1):
	#			self._grid_buffer[x][y] = 0
	#			self._grid_back_buffer[x][y] = 0
	
	def set_mode(mode):
		self._mode=mode

	def disconnect(self):
		self._parent = None
		self._matrix = None
		self._buttons = None   
		self._nav_up_button = None
		self._nav_down_button = None
		self._nav_left_button = None
		self._nav_right_button = None
		self._loop_length_inc_button = None
		self._loop_length_dec_button = None
		self._follow_button = None
		self._fold_button = None
		self._velocity_button = None
		self._mute_shift_button = None
		self._sequencer_clip = None
		self._lane_mute_buttons = None
		self._muted_lanes = None
		self._lock_button = None


	def update(self):
		if self._is_active:
			self.on_clip_slot_changed()
			self._update_nav_buttons()
			if( self._is_locked):
				if ((not self.application().view.is_view_visible('Detail')) or (not self.application().view.is_view_visible('Detail/Clip'))):
 					self.application().view.show_view('Detail')
 					self.application().view.show_view('Detail/Clip')
			if(self._mode==STEPSEQ_MODE_LANE_MUTE):
				self._update_lane_mute_buttons()
			else:	
				self._update_velocity_button()
				self._update_follow_button()
				self._update_quantization_button()
				self._update_fold_button()
				self._update_lock_button()
				self._update_velocity_shift_button()
				self._update_mute_shift_button()
				self._update_loop_length_inc_button()
				self._update_loop_length_dec_button()
			
			self._on_loop_changed()
			self._compute_key_indexes()
			self._update_matrix()
			self._on_playing_status_changed()

	def on_enabled_changed(self):
		self.update()

	def on_selected_track_changed(self):
		self.update()

	def on_track_list_changed(self):
		self.update()

	def on_selected_scene_changed(self):
		self.update()

	def on_scene_list_changed(self):
		self.update()



	def on_clip_slot_changed(self):
		if not self._is_locked:#self.is_enabled() and self._is_active:
			if self.song().view.highlighted_clip_slot != None:
				clip_slot = self.song().view.highlighted_clip_slot
				if clip_slot.has_clip: # and clip_slot.clip.is_midi_clip:
					if self._sequencer_clip != clip_slot.clip:
						#remove listeners
						if self._sequencer_clip != None:
							if self._sequencer_clip.is_midi_clip:
								if self._sequencer_clip.notes_has_listener(self._on_notes_changed):
									self._sequencer_clip.remove_notes_listener(self._on_notes_changed)
							if self._sequencer_clip.playing_status_has_listener(self._on_playing_status_changed):
								self._sequencer_clip.remove_playing_status_listener(self._on_playing_status_changed) 
							if self._sequencer_clip.loop_start_has_listener(self._on_loop_changed):
								self._sequencer_clip.remove_loop_start_listener(self._on_loop_changed) 
							if self._sequencer_clip.loop_end_has_listener(self._on_loop_changed):
								self._sequencer_clip.remove_loop_end_listener(self._on_loop_changed)							   
						#update reference
						
						self._sequencer_clip = clip_slot.clip
						self._loop_start = clip_slot.clip.loop_start
						self._loop_end = clip_slot.clip.loop_end
						self._loop_length = self._loop_end - self._loop_start  
						self._update_notes()
						self._on_loop_changed()
						
						#add listeners
						if self._sequencer_clip.is_midi_clip:
							if self._sequencer_clip.notes_has_listener(self._on_notes_changed):
								self._sequencer_clip.remove_notes_listener(self._on_notes_changed)
							self._sequencer_clip.add_notes_listener(self._on_notes_changed)		  
						if self._sequencer_clip.playing_status_has_listener(self._on_playing_status_changed):
							self._sequencer_clip.remove_playing_status_listener(self._on_playing_status_changed) 
						self._sequencer_clip.add_playing_status_listener(self._on_playing_status_changed)
						if self._sequencer_clip.loop_start_has_listener(self._on_loop_changed):
							self._sequencer_clip.remove_loop_start_listener(self._on_loop_changed)
						self._sequencer_clip.add_loop_start_listener(self._on_loop_changed)
						if self._sequencer_clip.loop_end_has_listener(self._on_loop_changed):
							self._sequencer_clip.remove_loop_end_listener(self._on_loop_changed)							   
						self._sequencer_clip.add_loop_end_listener(self._on_loop_changed)
				else:
					self._sequencer_clip=None
			else:
				self._sequencer_clip=None
						


	def _on_loop_changed(self): #loop start/end listener
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None:
				self._loop_start_index = int(self._sequencer_clip.loop_start / self._quantization / self._width)
				self._loop_end_index = int(self._sequencer_clip.loop_end / self._quantization / self._width) - 1 #round down to next button
				self._loop_length = self._sequencer_clip.loop_end - self._sequencer_clip.loop_start
				loop_index_length = self._loop_end_index - self._loop_start_index + 1
				if loop_index_length != self._loop_index_length:
					self._loop_index_length = loop_index_length
				if self._loop_start_index > (self._width -1):
					self._loop_start_index = -1
				elif self._loop_start_index < 0:
					self._loop_start_index = 0
				if self._loop_end_index > (self._width -1):
					self._loop_end_index = (self._width -1)
				elif self._loop_end_index < 0:
					self._loop_end_index = -1
# MUTE LANES

	def _update_lane_mute_buttons(self): #shifted lane mute buttons
		if self._is_active and self._mode==STEPSEQ_MODE_LANE_MUTE:
			if (self._lane_mute_buttons != None):
				for index in range(len(self._lane_mute_buttons)):
					self._lane_mute_buttons[(self._height - 1) - index].set_on_off_values(RED_FULL,RED_THIRD)
					#if index <= self._quantization_index:
						#self._lane_mute_buttons[index].turn_on()
					#self._lane_mute_buttons[(self._height - 1) - index].turn_on() #invert if using scene launch buttons
					#else:
					#self._lane_mute_buttons[index].turn_off()
					self._lane_mute_buttons[(self._height -1 ) - index].turn_off() #invert if using scene launch buttons					


	def _lane_mute_button_value(self, value, sender):
		assert (self._lane_mute_buttons != None)
		assert (list(self._lane_mute_buttons).count(sender) == 1)
		assert (value in range(128))
		if self.is_enabled() and self._is_active:
			if self._mode==STEPSEQ_MODE_LANE_MUTE and self._sequencer_clip != None:
				if ((value is not 0) or (not sender.is_momentary())):
					sender.turn_on()
					lane_to_mute = (self._height - 1) - (list(self._lane_mute_buttons).index(sender)) #invert to get top to bottom index
					pitch_to_mute = self._key_indexes[lane_to_mute] #invert top to bottom
					note_cache = list(self._clip_notes)
					for note in self._clip_notes:
						if note[0] == pitch_to_mute:
							mute = False
							if note[4] == False:
								mute = True
							note_to_mute = note
							note_cache.remove(note)
							note_cache.append([note_to_mute[0], note_to_mute[1], note_to_mute[2], note_to_mute[3], mute])
					self._sequencer_clip.select_all_notes()
					self._sequencer_clip.replace_selected_notes(tuple(note_cache)) 
				else:
					sender.turn_off() #turn LED off on button release

		
	def set_lane_mute_buttons(self, buttons):
		assert ((buttons == None) or (isinstance(buttons, tuple) and (len(buttons) == self._height)))
		if (self._lane_mute_buttons != buttons):
			if (self._lane_mute_buttons  != None):
				for button in self._lane_mute_buttons :
					button.remove_value_listener(self._lane_mute_button_value)
			self._lane_mute_buttons = buttons
			if (self._lane_mute_buttons  != None):
				for button in self._lane_mute_buttons :
					assert isinstance(button, ButtonElement)
					button.add_value_listener(self._lane_mute_button_value, identify_sender=True)
			##self._rebuild_callback()
			 
#NOTES CHANGES
	def _on_notes_changed(self): #notes changed listener
		if self.is_enabled() and self._is_active:
			self._update_notes()
			#self._parent._parent.schedule_message(1, self._update_notes)
			#Live bug: delay is required to avoid blocking mouse drag operations in MIDI clip view


	def _update_notes(self):
		"""LiveAPI clip.get_selected_notes returns a tuple of tuples where each inner tuple represents a note.
		The inner tuple contains pitch, time, duration, velocity, and mute state.
		e.g.: (46, 0.25, 0.25, 127, False)"""
		#if self.is_enabled() and self._is_active:
		if self._sequencer_clip!= None and self._sequencer_clip.is_midi_clip:
			self._sequencer_clip.select_all_notes()
			note_cache = self._sequencer_clip.get_selected_notes()
			self._sequencer_clip.deselect_all_notes()
			if self._clip_notes != note_cache:
				self._clip_notes = note_cache
				self._compute_key_indexes()
				self._update_matrix()

#PLAY POSITION

	def _on_playing_status_changed(self): #playing status changed listener
		if True:#self.is_enabled() and self._is_active:
			if self._sequencer_clip != None:
				if self._sequencer_clip.is_playing:
					if self._sequencer_clip.playing_position_has_listener(self._on_playing_position_changed):
						self._sequencer_clip.remove_playing_position_listener(self._on_playing_position_changed)
					self._sequencer_clip.add_playing_position_listener(self._on_playing_position_changed)
				else:
					if self._sequencer_clip.playing_position_has_listener(self._on_playing_position_changed):
						self._sequencer_clip.remove_playing_position_listener(self._on_playing_position_changed)


	def _on_playing_position_changed(self): #playing position changed listener
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None:
				"""LiveAPI clip.playing_position: Constant access to the current playing position of the clip.
				The returned value is the position in beats for midi and warped audio clips,
				or in seconds for unwarped audio clips. Stopped clips will return 0."""
				position = self._sequencer_clip.playing_position #position in beats (1/4 notes in 4/4 time)
				bank = int(position / self._quantization / self._width) # 0.25 for 16th notes;  0.5 for 8th notes
				if self._is_following == True:
					if self._bank_index != bank:
						self._bank_index = bank
						self._update_nav_buttons()
				self._update_matrix()

# MATRIX
	def _update_matrix(self): #step grid LEDs are updated here
		if self.is_enabled() and self._is_active:
			#clear back buffer
			for x in range(self._width):
				for y in range(self._width):
					self._grid_back_buffer[x][y] = 0
			
			#update back buffer
			if self._sequencer_clip != None:# and self._sequencer_clip.is_midi_clip:
				if self._sequencer_clip.is_midi_clip:
					
					#add play positition in amber
					position = self._sequencer_clip.playing_position #position in beats (1/4 notes in 4/4 time)
					grid_play_bank = int(position / self._quantization / self._width)%self._height # 0.25 for 16th notes;  0.5 for 8th notes
					grid_play_position = int(position / self._quantization) - (grid_play_bank * self._width) #stepped postion
					#play back position
					if self._sequencer_clip.is_playing:
						self._grid_back_buffer[grid_play_position][grid_play_bank]=AMBER_HALF
					
					for note in self._clip_notes:
						position = note[1] #position in beats; range is 0.x to 15.x for 4 measures in 4/4 time (equivalent to 1/4 notes)
						bank = int(position / self._quantization / self._width) #at 1/16th resolution in 4/4 time, each bank is 1/2 measure wide
						grid_x_position = int(position / self._quantization) - (bank * self._width) #stepped postion at quantize resolution
						key = note[0] #key: 0-127 MIDI note #
						#if key >= self._key_index and key < (self._key_index + self._height):
						index = index_of(self._key_indexes,key)
						if index!=-1:
							index=7-index
							#grid_y_position = self._key_index + self._height -1 - key #invert bottom to top, to match button order
							grid_y_position=index
							velocity = note[3]
							muted = note[4]
							velocity_color=LED_OFF
							if (not muted) and bank == grid_play_bank and grid_play_position==grid_x_position and self._sequencer_clip.is_playing:
								#highligh playing notes in red. even if they are from other banks.
								velocity_color = RED_THIRD
								for index in range(len(VELOCITY_MAP)):
									if velocity>=VELOCITY_MAP[index]:
										velocity_color=VELOCITY_COLOR_HIGHLIGHT_MAP[index]
								self._grid_back_buffer[grid_x_position][grid_y_position]=velocity_color;
							elif bank == self._bank_index: #if note is in current bank, then update grid
								if muted:
									velocity_color = RED_THIRD
								else:
									velocity_color = GREEN_THIRD
									for index in range(len(VELOCITY_MAP)):
										if velocity>=VELOCITY_MAP[index]:
											velocity_color=VELOCITY_COLOR_MAP[index]
								if self._grid_back_buffer[grid_x_position][grid_y_position]==0:#do not erase current note highlight
									self._grid_back_buffer[grid_x_position][grid_y_position]=velocity_color;
	
			#caching : compare back buffer to buffer and update grid. this should minimize midi traffic quite a bit.
			for x in range(self._width):
				for y in range(self._width):
					if(self._grid_back_buffer[x][y]!=self._grid_buffer[x][y] or self._force_update):
						self._grid_buffer[x][y] = self._grid_back_buffer[x][y] 
						self._matrix.send_value(x, y, self._grid_buffer[x][y])
			self._force_update=False
			

	def _matrix_value(self, value, x, y, is_momentary): #matrix buttons listener
		if self.is_enabled() and self._is_active:
			if ((value != 0) or (not is_momentary)):
				#self._parent._parent.log_message(str(x)+"."+str(y)+"."+str(value)+" "+"scheduled")
				self._parent._parent.schedule_message(1, self._matrix_value_message,[value,x,y,is_momentary])
	
	def _matrix_value_message(self, values): #value, x, y, is_momentary): #matrix buttons listener
		value = values[0]
		x = values[1]
		y = values[2]
		is_momentary=values[3]
		
		#self._parent._parent.log_message(str(x)+"."+str(y)+"."+str(value)+" "+ "processing")
	
		assert (self._buttons != None)
		assert (value in range(128))
		assert (x in range(self._buttons.width()))
		assert (y in range(self._buttons.height()))
		assert isinstance(is_momentary, type(False))
		"""(pitch, time, duration, velocity, mute state)
		e.g.: (46, 0.25, 0.25, 127, False)"""
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None and self._sequencer_clip.is_midi_clip:
				if ((value != 0) or (not is_momentary)):
					#pitch = (self._key_index + self._height - 1) - y #invert top to bottom
					#self._parent._parent.log_message("y:"+str(y))
					pitch = self._key_indexes[7-y]
					time = (x + (self._bank_index * self._width)) * self._quantization #convert position to time in beats
					velocity = self._velocity
					duration = self._quantization # 0.25 = 1/16th note; 0.5 = 1/8th note
					note_cache = list(self._clip_notes)
					for note in note_cache:
						if pitch == note[0] and time == note[1]:
							if self._is_velocity_shifted:
								#update velocity of the note
								new_velocity_index=0
								for index in range(len(VELOCITY_MAP)):
									if note[3]>=VELOCITY_MAP[index]:
										new_velocity_index=(index+1)%len(VELOCITY_MAP)
								note_cache.append([note[0], note[1], note[2], VELOCITY_MAP[new_velocity_index], note[4]])
							elif not self._is_mute_shifted:
								note_cache.remove(note)
							else:
								#mute / un mute note.
								note_cache.append([note[0], note[1], note[2], note[3], not note[4]])
							break
					else:
						note_cache.append([pitch, time, duration, velocity, self._is_mute_shifted])
					self._sequencer_clip.select_all_notes()
					self._sequencer_clip.replace_selected_notes(tuple(note_cache))


	def set_button_matrix(self, buttons):
		assert isinstance(buttons, (ButtonMatrixElement, type(None)))
		if (buttons != self._buttons):
			if (self._buttons != None):
				self._buttons.remove_value_listener(self._matrix_value)
			self._buttons = buttons
			if (self._buttons != None):
				self._buttons.add_value_listener(self._matrix_value)
			##self._rebuild_callback()
			self.update()
			
#FOLD NOTE
	def _compute_key_indexes(self,force=False):
		if self._is_fold:
			if force:
				#when switching to fold mode 
				key_index=self._key_indexes[0] #use previous base key
				new_key_index = key_index #set default value if not match found
				#find base note
				inc=0
				found=False
				while not found and (key_index+inc<127 or key_index-inc>0):
					if self._is_used(key_index+inc):#look upwards
						new_key_index=key_index+inc
						found=True
						#self._parent._parent.log_message("found base note: +"+str(inc))
					if self._is_used(key_index-inc):#look downwards
						new_key_index=key_index-inc
						found=True
						#self._parent._parent.log_message("found base note: -"+str(inc))
					inc=inc+1
				self._key_indexes[0]=new_key_index #set found value
				#fill in the 7 other lanes with notes
				for i in range(7):
					key_index=self._key_indexes[i+1 -1] +1 #set base for search
					new_key_index=key_index # set an initial value if no match found
					found=False
					inc=0
					while not found and (key_index+inc<127):
						if self._is_used(key_index+inc):
							new_key_index=key_index+inc
							found=True
							#self._parent._parent.log_message("found note"+str(i+1)+": +"+str(inc))
						inc=inc+1
					self._key_indexes[i+1]=new_key_index #set found value
		else:
			#when switching to unfold mode
			new_key_index=self._key_indexes[0]
			for i in range(8): # set the 8 lanes incrementally
				self._key_indexes[i]=new_key_index+i
		
		#self._parent._parent.log_message("keys : ")
		#for i in range(8):
		#	self._parent._parent.log_message(str(i)+" : "+str(self._key_indexes[i]))
		

	def _is_used(self,key):
		if self._sequencer_clip != None:# and self._sequencer_clip.is_midi_clip:
			if self._sequencer_clip.is_midi_clip:
				for note in self._clip_notes:
					if note[0]==key: #key: 0-127 MIDI note #
						return(True)
			else:
				return(False)
		return(False)
		


# LOOP LENGTH

	def set_loop_length_dec_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (self._loop_length_dec_button != button) and self._mode==STEPSEQ_MODE_NORMAL:
			if (self._loop_length_dec_button  != None):
				self._loop_length_dec_button.remove_value_listener(self._loop_length_dec_button_value)
			self._loop_length_dec_button = button
			if (self._loop_length_dec_button  != None):
				assert isinstance(button, ButtonElement)
				self._loop_length_dec_button.add_value_listener(self._loop_length_dec_button_value, identify_sender=True)
			##self._rebuild_callback()


	def _loop_length_dec_button_value(self, value, sender):
		assert (self._loop_length_dec_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if self._sequencer_clip != None:
				if ((value is not 0) or (not sender.is_momentary())):
					self._loop_index_length = self._loop_index_length - 1
					self._loop_end = self._sequencer_clip.loop_start + (self._loop_index_length * self._width * self._quantization)
					self._sequencer_clip.loop_end = self._loop_end
			self._update_nav_buttons()
			
	def _update_loop_length_dec_button(self):
		if self._is_active:
			if (self._loop_length_dec_button != None) and self._mode==STEPSEQ_MODE_NORMAL:
				self._loop_length_dec_button.set_on_off_values(GREEN_THIRD,LED_OFF)
				self._loop_length_dec_button.turn_on()

	def set_loop_length_inc_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (self._loop_length_inc_button != button):
			if (self._loop_length_inc_button  != None):
				self._loop_length_inc_button.remove_value_listener(self._loop_length_inc_button_value)
			self._loop_length_inc_button = button
			if (self._loop_length_inc_button  != None):
				assert isinstance(button, ButtonElement)
				self._loop_length_inc_button.add_value_listener(self._loop_length_inc_button_value, identify_sender=True)
			##self._rebuild_callback()


	def _loop_length_inc_button_value(self, value, sender):
		assert (self._loop_length_inc_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if self._sequencer_clip != None:
				if ((value is not 0) or (not sender.is_momentary())):
					self._loop_index_length = self._loop_index_length + 1
					self._loop_end = self._sequencer_clip.loop_start + (self._loop_index_length * self._width * self._quantization)
					self._sequencer_clip.loop_end = self._loop_end
			self._update_nav_buttons()

	def _update_loop_length_inc_button(self):
		if self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if (self._loop_length_inc_button != None):
				self._loop_length_inc_button.set_on_off_values(GREEN_THIRD,LED_OFF)
				self._loop_length_inc_button.turn_on()


# QUANTIZE
	def _update_quantization_button(self):
		if self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if (self._quantization_button != None):
				self._quantization_button.set_on_off_values(QUANTIZATION_COLOR_MAP[self._quantization_index],LED_OFF)
				self._quantization_button.turn_on()
		

	def set_quantization_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (self._velocity_button != button):
			if (self._quantization_button  != None):
				self._quantization_button.remove_value_listener(self._quantization_button_value)
			self._quantization_button = button
			if (self._quantization_button  != None):
				assert isinstance(button, ButtonElement)
				self._quantization_button.add_value_listener(self._quantization_button_value, identify_sender=True)
			##self._rebuild_callback()
			self._update_quantization_button()

	def _quantization_button_value(self, value, sender):
		assert (self._velocity_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if ((value is not 0) or (not sender.is_momentary())):
				self._quantization_index = (self._quantization_index+1)%len(QUANTIZATION_MAP)
				self._quantization = QUANTIZATION_MAP[self._quantization_index]
				self._update_quantization_button()	
				self.update()				


# VELOCITY
	def _update_velocity_button(self):
		if self._is_active:
			if (self._velocity_button != None) and self._mode==STEPSEQ_MODE_NORMAL:
				self._velocity_button.set_on_off_values(VELOCITY_COLOR_MAP[self._velocity_index],LED_OFF)
				self._velocity_button.turn_on()

	def set_velocity_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (self._velocity_button != button):
			if (self._velocity_button  != None):
				self._velocity_button.remove_value_listener(self._velocity_button_value)
			self._velocity_button = button
			if (self._velocity_button  != None):
				assert isinstance(button, ButtonElement)
				self._velocity_button.add_value_listener(self._velocity_button_value, identify_sender=True)
			##self._rebuild_callback()
			self._update_velocity_button()

	def _velocity_button_value(self, value, sender):
		assert (self._velocity_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if ((value is not 0) or (not sender.is_momentary())):
				self._velocity_index = (self._velocity_index+1)%len(VELOCITY_MAP)
				self._velocity = VELOCITY_MAP[self._velocity_index]
				self._update_velocity_button()	
					


# FOLLOW
	def _update_follow_button(self):
		if self._is_active:
			if (self._follow_button != None) and self._mode==STEPSEQ_MODE_NORMAL:
				if self._is_following:
					self._follow_button.set_on_off_values(AMBER_FULL,AMBER_THIRD)
					self._follow_button.turn_on()
				else:
					self._follow_button.set_on_off_values(AMBER_FULL,AMBER_THIRD)
					self._follow_button.turn_off()

	def set_follow_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (button != self._follow_button):
			if (self._follow_button != None):
				self._follow_button.remove_value_listener(self._follow_value)
			self._follow_button = button
			if (self._follow_button != None):
				self._follow_button.add_value_listener(self._follow_value,identify_sender=True)
			##self._rebuild_callback()


	def _follow_value(self, value,sender):
		assert (self._follow_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if ((value is not 0) or (not sender.is_momentary())):
				self._is_following = (not self._is_following) 
				self._update_nav_buttons() 
				self._update_follow_button()


# LOCK
	def _update_lock_button(self):
		if self._is_active:
			if (self._lock_button != None) and self._mode==STEPSEQ_MODE_NORMAL:
				if self._is_locked:
					self._lock_button.set_on_off_values(RED_FULL,RED_THIRD)
					self._lock_button.turn_on()
				else:
					self._lock_button.set_on_off_values(RED_FULL,RED_THIRD)
					self._lock_button.turn_off()

	def set_lock_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (button != self._lock_button):
			if (self._lock_button != None):
				self._lock_button.remove_value_listener(self._lock_value)
			self._lock_button = button
			if (self._lock_button != None):
				self._lock_button.add_value_listener(self._lock_value,identify_sender=True)
			##self._rebuild_callback()


	def _lock_value(self, value,sender):
		assert (self._lock_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if ((value is not 0) or (not sender.is_momentary())):
				self._is_locked = (not self._is_locked) 
				self._update_lock_button()



# FOLD 
	def _update_fold_button(self): 
		if self._is_active:
			if (self._fold_button != None) and self._mode==STEPSEQ_MODE_NORMAL:
				if self._is_fold:
					self._fold_button.set_on_off_values(GREEN_FULL,GREEN_THIRD)
					self._fold_button.turn_on()
				else:
					self._fold_button.set_on_off_values(GREEN_FULL,GREEN_THIRD)
					self._fold_button.turn_off()


	def set_fold_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (button != self._fold_button):
			if (self._fold_button != None):
				self._fold_button.remove_value_listener(self._fold_value)
			self._fold_button = button
			if (self._fold_button != None):
				self._fold_button.add_value_listener(self._fold_value,identify_sender=True)


	def _fold_value(self, value, sender):
		assert (self._fold_button != None)
		assert (value in range(128))
		if self.is_enabled()and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			if ((value is not 0) or (not sender.is_momentary())):
				self._is_fold = not self._is_fold
				if self._is_fold:
					self._fold_button.turn_on()
				else:
					self._fold_button.turn_off()
				self._compute_key_indexes(True)
				self._update_matrix()




# VELOCITY SHIFT
	def _update_velocity_shift_button(self): 
		if self._is_active:
			if (self._velocity_shift_button != None) and self._mode==STEPSEQ_MODE_NORMAL:
				if self._is_velocity_shifted:
					self._velocity_shift_button.set_on_off_values(GREEN_FULL,GREEN_THIRD)
					self._velocity_shift_button.turn_on()
				else:
					self._velocity_shift_button.set_on_off_values(GREEN_FULL,GREEN_THIRD)
					self._velocity_shift_button.turn_off()


	def set_velocity_shift_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (button != self._velocity_shift_button):
			if (self._velocity_shift_button != None):
				self._velocity_shift_button.remove_value_listener(self._velocity_shift_value)
			self._velocity_shift_button = button
			if (self._velocity_shift_button != None):
				self._velocity_shift_button.add_value_listener(self._velocity_shift_value)


	def _velocity_shift_value(self, value):
		assert (self._velocity_shift_button != None)
		assert (value in range(128))
		if self.is_enabled()and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			self._is_velocity_shifted = not self._is_velocity_shifted 
			if self._is_velocity_shifted:
				self._velocity_shift_button.turn_on()
			else:
				self._velocity_shift_button.turn_off()



# SHIFT
	def _update_mute_shift_button(self): 
		if self._is_active:
			if (self._mute_shift_button != None) and self._mode==STEPSEQ_MODE_NORMAL:
				if self._is_mute_shifted:
					self._mute_shift_button.set_on_off_values(RED_FULL,RED_THIRD)
					self._mute_shift_button.turn_on()
				else:
					self._mute_shift_button.set_on_off_values(RED_FULL,RED_THIRD)
					self._mute_shift_button.turn_off()


	def set_mute_shift_button(self, button):
		assert (isinstance(button,(ButtonElement,type(None))))
		if (button != self._mute_shift_button):
			if (self._mute_shift_button != None):
				self._mute_shift_button.remove_value_listener(self._mute_shift_value)
			self._mute_shift_button = button
			if (self._mute_shift_button != None):
				self._mute_shift_button.add_value_listener(self._mute_shift_value)


	def _mute_shift_value(self, value):
		assert (self._mute_shift_button != None)
		assert (value in range(128))
		#self._parent._parent.log_message(str(self._mode))
		if self.is_enabled()and self._is_active and self._mode==STEPSEQ_MODE_NORMAL:
			#if value > 0:
			self._is_mute_shifted = not self._is_mute_shifted
			if self._is_mute_shifted:
				self._mute_shift_button.turn_on()
			else:
				self._mute_shift_button.turn_off()


# NAV 
	def set_nav_buttons(self, up, down, left, right):
		assert isinstance(up, (ButtonElement,type(None)))
		assert isinstance(down, (ButtonElement,type(None)))
		assert isinstance(left, (ButtonElement,type(None)))
		assert isinstance(right, (ButtonElement,type(None)))
		if (self._nav_up_button != None):
			self._nav_up_button.remove_value_listener(self._nav_up_value)
		self._nav_up_button = up
		if (self._nav_up_button != None):
			self._nav_up_button.add_value_listener(self._nav_up_value)
		if (self._nav_down_button != None):
			self._nav_down_button.remove_value_listener(self._nav_down_value)
		self._nav_down_button = down
		if (self._nav_down_button != None):
			self._nav_down_button.add_value_listener(self._nav_down_value)
		if (self._nav_left_button != None):
			self._nav_left_button.remove_value_listener(self._nav_left_value)
		self._nav_left_button = left
		if (self._nav_left_button != None):
			self._nav_left_button.add_value_listener(self._nav_left_value)
		if (self._nav_right_button != None):
			self._nav_right_button.remove_value_listener(self._nav_right_value)
		self._nav_right_button = right
		if (self._nav_right_button != None):
			self._nav_right_button.add_value_listener(self._nav_right_value)
		#self.update()


	def _nav_up_value(self, value):
		assert (self._nav_up_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active:
			if self._is_mute_shifted:
				pass
			else:
				button_is_momentary = self._nav_up_button.is_momentary()
				if button_is_momentary:
					if (value != 0):
						self._scroll_up_ticks_delay = INITIAL_SCROLLING_DELAY
					else:
						self._scroll_up_ticks_delay = -1			
				if ((value != 0) or (not self._nav_up_button.is_momentary())):
					if self._key_indexes[0] < (128 - self._height):
						self._key_indexes[0] += 1
						self._compute_key_indexes(True)
						self._update_matrix()


	def _nav_down_value(self, value):
		assert (self._nav_down_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active:
			if self._is_mute_shifted:
				pass
			else:
				button_is_momentary = self._nav_down_button.is_momentary()
				if button_is_momentary:
					if (value != 0):
						self._scroll_down_ticks_delay = INITIAL_SCROLLING_DELAY
					else:
						self._scroll_down_ticks_delay = -1			
				if ((value != 0) or (not self._nav_down_button.is_momentary())):
					if self._key_indexes[0] > 0:
						self._key_indexes[0] -= 1
						self._compute_key_indexes(True)
						self._update_matrix()


	def _nav_left_value(self, value):
		assert (self._nav_left_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active:
			if self._is_mute_shifted:
				pass
			else:
				button_is_momentary = self._nav_left_button.is_momentary()
				if button_is_momentary:
					if (value != 0):
						self._scroll_left_ticks_delay = INITIAL_SCROLLING_DELAY
					else:
						self._scroll_left_ticks_delay = -1			
				if ((value != 0) or (not self._nav_left_button.is_momentary())):
					if self._bank_index > 0:
						self._bank_index -= 1
						self._update_nav_buttons()
						self._update_matrix()


	def _nav_right_value(self, value):
		assert (self._nav_right_button != None)
		assert (value in range(128))
		if self.is_enabled() and self._is_active:
			if self._is_mute_shifted:
				pass
			else:
				button_is_momentary = self._nav_right_button.is_momentary()
				if button_is_momentary:
					if (value != 0):
						self._scroll_right_ticks_delay = INITIAL_SCROLLING_DELAY
					else:
						self._scroll_right_ticks_delay = -1			
				if ((value != 0) or (not self._nav_right_button.is_momentary())):
					if (self._bank_index)<self._loop_end_index:
						self._bank_index += 1
						self._update_nav_buttons()
						self._update_matrix()

	def _update_nav_buttons(self):
		if self.is_enabled() and self._is_active:
			if self._sequencer_clip != None and self._sequencer_clip.is_midi_clip:
				if self._bank_index==0:
					self._nav_left_button.set_on_off_values(GREEN_THIRD,0)
					self._nav_left_button.turn_on()
				else:
					self._nav_left_button.set_on_off_values(GREEN_FULL,0)
					self._nav_left_button.turn_on()
			
				if (self._bank_index)>=self._loop_end_index:
					self._nav_right_button.set_on_off_values(GREEN_THIRD,0)
					self._nav_right_button.turn_on()
				else:
					self._nav_right_button.set_on_off_values(GREEN_FULL,0)
					self._nav_right_button.turn_on()
				
				if self._key_indexes[0]>0:
					self._nav_down_button.set_on_off_values(GREEN_FULL,0)
					self._nav_down_button.turn_on()
				else:
					self._nav_down_button.set_on_off_values(GREEN_THIRD,0)
					self._nav_down_button.turn_on()
					
				if self._key_indexes[0]<126:
					self._nav_up_button.set_on_off_values(GREEN_FULL,0)
					self._nav_up_button.turn_on()
				else:
					self._nav_up_button.set_on_off_values(GREEN_THIRD,0)
					self._nav_up_button.turn_on()
			else:
				self._nav_left_button.set_on_off_values(LED_OFF,LED_OFF)
				self._nav_left_button.turn_off()
				self._nav_right_button.set_on_off_values(LED_OFF,LED_OFF)	
				self._nav_right_button.turn_off()
				self._nav_down_button.set_on_off_values(LED_OFF,LED_OFF)
				self._nav_down_button.turn_off()
				self._nav_up_button.set_on_off_values(LED_OFF,LED_OFF)
				self._nav_up_button.turn_off()
					

	def _on_timer(self):
		if self.is_enabled() and self._is_active:
			scroll_delays = [self._scroll_up_ticks_delay,self._scroll_down_ticks_delay,self._scroll_right_ticks_delay,self._scroll_left_ticks_delay]
			if (scroll_delays.count(-1) < 4):
				bank_increment = 0
				key_increment = 0
				if (self._scroll_right_ticks_delay > -1):
					if self._is_scrolling():
						bank_increment += 1
						self._scroll_right_ticks_delay = INTERVAL_SCROLLING_DELAY
					self._scroll_right_ticks_delay -= 1
				if (self._scroll_left_ticks_delay > -1):
					if self._is_scrolling():
						bank_increment -= 1
						self._scroll_left_ticks_delay = INTERVAL_SCROLLING_DELAY
					self._scroll_left_ticks_delay -= 1
				if (self._scroll_down_ticks_delay > -1):
					if self._is_scrolling():
						key_increment -= 1
						self._scroll_down_ticks_delay = INTERVAL_SCROLLING_DELAY
					self._scroll_down_ticks_delay -= 1
				if (self._scroll_up_ticks_delay > -1):
					if self._is_scrolling():
						key_increment += 1
						self._scroll_up_ticks_delay = INTERVAL_SCROLLING_DELAY
					self._scroll_up_ticks_delay -= 1
				if (self._bank_index + bank_increment) < self._width and (self._bank_index + bank_increment) >= 0:
					if self._bank_index + bank_increment != self._bank_index:
						self._bank_index = self._bank_index + bank_increment
						self._update_nav_buttons()
						self._update_matrix()
				if (self._key_indexes[0] + key_increment) < (128 - self._height + 1) and (self._key_indexes[0] + key_increment) >=0:
					if self._key_indexes[0] + key_increment != self._key_indexes[0]:
						self._key_indexes[0] = self._find_next_note(self._key_indexes[0],key_increment)
						#self._parent._parent.log_message(" : "+str(self._key_indexes[0]))
						self._compute_key_indexes(True)
						self._update_matrix()

	def _find_next_note(self,index,increment):
		return(index+increment)


	def _is_scrolling(self):
		return (0 in (self._scroll_up_ticks_delay,self._scroll_down_ticks_delay,self._scroll_right_ticks_delay,self._scroll_left_ticks_delay))
