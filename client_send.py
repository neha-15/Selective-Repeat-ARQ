import sys
import socket
import signal
import time
import math
import psutil
import os
import re
import fcntl

def create_seq(seq_file1):
	global mss
	global filetotransfer
	
	seq_file=open(seq_file1,'a')
	sequence=0
	seq_file.write(str(sequence)+',\n')
	with open(filetotransfer,'rb') as file_tg:
		while 1:
				pos=(sequence+1)*mss
				file_tg.seek(pos,0)
				data=file_tg.read(1)
				if not data:
					break
				sequence=sequence+1
				seq_file.write(str(sequence)+',\n')
	file_tg.close()
	seq_file.close()

def ackrecv(s,seq_file1):
	pid=os.fork()
	if (pid==0):
		while True:

				data,addr=s.recvfrom(65535)
				seq_no=validate_recv_msg(data)
				if seq_no!=-1:
					mark_seqno_ack(seq_no,seq_file1)
				
				
def mark_seqno_ack(seq_no,seq_file1):
	file_desc = open(seq_file1, "r+w")
	fcntl.flock(file_desc.fileno(),fcntl.LOCK_EX)
	data = file_desc.readlines()
	if data[int(seq_no)] == seq_no + ",A\n":
		#print "got ack:" + str(seq_no)
        	data[int(seq_no)] = seq_no + ",D\n"
	new_data = ''.join(data)
        file_desc.seek(0)
	file_desc.truncate()	
	file_desc.write(new_data)
        file_desc.close()


'''validate the ack message recieved from the server'''
def validate_recv_msg(msg):
	seq_no = str(int(msg[0:32],2))
	pad = msg[32:48]
	ack_ind = msg[48:]
	if pad == ('0' * 16) and ack_ind == ('10' * 8):
		return seq_no
	return -1


def tf(seq_file1):
	progress=0
	seq_file=open(seq_file1,'r')

	
	fcntl.flock(seq_file.fileno(),fcntl.LOCK_EX)
	
	
	

	for i in seq_file:
		if(i!='\n'):
			stat=re.findall('\d+,([D])\n',i)
			if not stat:
					progress=-1

					break

	seq_file.close()

	return progress


def recv_seq_no(seq_file1):
	global windowsize
	seq_no=-1
	seq_file=open(seq_file1,'r')
	fcntl.flock(seq_file.fileno(),fcntl.LOCK_EX)

	count=0
	
	for line in reversed(seq_file.readlines()):
		if re.findall('(\d+),A\n',line):
			count+=1
		elif re.findall('(\d+),\n',line):
			seq_no=str(re.findall('(\d+),\n',line)[0])


	seq_file.close()
	if count==windowsize:
		return -1
	elif count<windowsize:
		return seq_no
	else:
		print "Something is wrong"
		return -1

def active_seq_no(seq_no,seq_file1):
	seq_file=open(seq_file1,'r+w')
	fcntl.flock(seq_file.fileno(),fcntl.LOCK_EX)
	data=seq_file.readlines()
	if data[int(seq_no)]==seq_no+",\n":
			data[int(seq_no)]=seq_no+",A\n"
	data_new=''.join(data)
	seq_file.seek(0)
	seq_file.truncate()
	seq_file.write(data_new)
	seq_file.close()

def rdt_send(filetotransfer,seq_no):
	global mss
	data=''
	with open(filetotransfer,'rb') as file_data:
		index=seq_no*mss
		file_data.seek(index,0)
		for i in range(1,mss+1):
			fdata=file_data.read(1)
			if fdata:
				data=data+str(fdata)
	file_data.close()
	head=datagram(seq_no,data)
	data_with_checksum=calcchecksum(head)
	return data_with_checksum

def calcchecksum(msg):
        if msg:
		total = 0	
                data = [msg[i:i+16] for i in range(0,len(msg),16)]
                for y in data:
			total += int(y,2)
			if total >= 65535:
				total -= 65535
		checksum = 65535 - total
		check_sum_bits = '{0:016b}'.format(checksum)
		send_msg = msg[0:32] + check_sum_bits + msg[48:]
		return send_msg
	else:
		return '0'


def datagram(seq_no,segment_data):
	seq_no_bits = '{0:032b}'.format(seq_no)
    	checksum = '0' * 16
    	indicator_bits = '01' * 8
    	data = ''
    	for i in range(1,len(segment_data)+1):
        	data_character = segment_data[i-1]
        	data_byte = '{0:08b}'.format(ord(data_character))
        	data = data + data_byte
    	segment = seq_no_bits + checksum + indicator_bits + data
    	return segment

def timer_thread(seq_no,seq_file1):
	parent_process=os.fork()
	if parent_process==0:
		proc=psutil.Process(os.getpid())
		proc.set_nice(15)
		time.sleep(0.5)
		seq_file=open(seq_file1,'r+w')
		fcntl.flock(seq_file.fileno(),fcntl.LOCK_EX)
		data=seq_file.readlines()
		update_seq=-1
		for line in data:
				match = re.findall('(\d+),(\w)\n',line)
				if match:
					if seq_no==str(match[0][0]):
						if str(match[0][1]) == 'D':
							
							break
						elif str(match[0][1]) == 'A':
							print "Timer Expired, Sequence number= "+seq_no
							update_seq=1
							break
						else:
							break

		if(update_seq==1):
			if data[int(seq_no)]==seq_no + ",A\n":
					data[int(seq_no)]=seq_no + ",\n"
			data_new=''.join(data)
			seq_file.seek(0)
			seq_file.truncate()
			seq_file.write(data_new)
		seq_file.close()
		os._exit(0)



serverip=str(sys.argv[1])
serverport=int(sys.argv[2])
filetotransfer=str(sys.argv[3])
windowsize=int(sys.argv[4])
mss=int(sys.argv[5])
seq_file="tg.txt"

print "Window Size="+str(windowsize)
print "Mss="+str(mss)

clientname=socket.gethostbyname(socket.gethostname())
s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
os.system('rm tg.txt')
create_seq(seq_file)


ackrecv(s,seq_file)
start_time=time.time()
while True:

		proc=psutil.Process(os.getpid())
		proc.set_nice(5)
		stat=tf(seq_file)
		if stat==0:
			 print "Process Completed"
			 end_time=time.time()
			 print "Time Taken="+str(end_time-start_time)
			 break

		seq_to_send=recv_seq_no(seq_file)

		if seq_to_send>-1:

			active_seq_no(seq_to_send,seq_file)
			msg2send=rdt_send(filetotransfer,int(seq_to_send))
			
			s.sendto(msg2send,(serverip,serverport))
			timer_thread(seq_to_send,seq_file)

print "Exit"
s.close()
