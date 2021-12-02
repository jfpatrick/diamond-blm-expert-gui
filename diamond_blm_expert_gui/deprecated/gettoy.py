import pyjapc
import time
import numpy as np

from datetime import datetime, timedelta, timezone


print("starting")

japc = pyjapc.PyJapc()
japc.setSelector("")


japc.rbacLogin(loginDialog=True)



device = "SP.BA6.BLMDIAMOND.2"
property = "AcquisitionHistogram"

while True:

	field_values = japc.getParam("{}/{}".format(device, property), timingSelectorOverride="SPS.USER.SFTPRO1", getHeader=True, noPyConversion=False)
	get_ts = field_values[1]["acqStamp"]
	current_ts = datetime.now(timezone.utc)

	"""
	if current_ts - get_ts < timedelta(seconds = 2):
		isworking = True
	else:
		isworking = False
	"""

	if current_ts - get_ts < timedelta(seconds = 0.125):
		
		# do a second get
		pass

		time.sleep(0.125)

		field_values = japc.getParam("{}/{}".format(device, property), timingSelectorOverride="SPS.USER.SFTPRO1", getHeader=True, noPyConversion=False)
		get_ts = field_values[1]["acqStamp"]
		current_ts = datetime.now(timezone.utc)

		print("a")

		if current_ts - get_ts < timedelta(seconds = 0.125):
			isworking = True
		else:
			isworking = False



	else:



		isworking = False



	
	print("current: {}, get: {}, working: {}".format(current_ts, get_ts, isworking))


	time.sleep(0.5)
