# Launchpad fix for colour blind users
# ST8 <st8@q3f.org>
# January 2011

import Live
from Launchpad.Launchpad import Launchpad
from Launchpad.SubSelectorComponent import *

class LaunchpadColour(Launchpad):

	def __init__(self, c_instance):
		Launchpad.__init__(self, c_instance)
		self.set_colours()
		

		
	def set_colours(self):
		for scene_index in range(self._selector._matrix.height()):
			scene = self._selector._session.scene(scene_index)
			scene.set_triggered_value(GREEN_BLINK)
			for track_index in range(self._selector._matrix.width()):
				clip_slot = scene.clip_slot(track_index)
				clip_slot.set_triggered_to_play_value(AMBER_BLINK)
				clip_slot.set_triggered_to_record_value(RED_BLINK)
				clip_slot.set_stopped_value(GREEN_FULL)
				clip_slot.set_started_value(GREEN_BLINK)
				clip_slot.set_recording_value(RED_FULL)
