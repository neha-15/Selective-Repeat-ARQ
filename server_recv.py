from socket import *
from decimal import *
import os, random, time,sys


def gen_random_number():
        while 1:
                gen_number = random.uniform(0,1)
                if Decimal(gen_number) != Decimal(0.0):
                        break
	return gen_number


def rdt_send(message):
	seq_no = message[0:32]
	pad = '0' * 16
	ack_ind = '10' * 8
	return seq_no + pad + ack_ind

'''write data recieved in the packet to the file'''
def write_file(message,filename):
	file_desc = open(filename,'a')
	msg = str(message[64:])
	iterations = len(msg)/8
	final_data = ''
	for i in range(0,iterations):
		bit_data = str(msg[i*8:(i+1)*8])
		char_data = chr(int(bit_data, 2))
		final_data = final_data + char_data
	file_desc.write(final_data)
	file_desc.close()
	return int(message[0:32],2) + 1


'''write the seqno and data in a buffer'''
def write_buff(message,buff_name):
	buff_name[int(message[0:32],2)] = message

'''calculate the checksum return 1 if correct else -1'''
def cal_checksum(msg):
	if msg[48:64] == '01' * 8:
		total = 0
                data = [msg[i:i+16] for i in range(0,len(msg),16)]
                for y in data:
                        total += int(y,2)
                        if total >= 65535:
                                total -= 65535
                if total == 0:
			return 1
		else:
			return -1
	else:
		return -1


'''''''''Main Program'''''''''''
#print sys.argv
if(len(sys.argv) == 4):
	
	port = int(sys.argv[1])
	filename = sys.argv[2]
	probability = float(sys.argv[3])
else:
	print "Wrong set of arguments passed"
	exit(0)


if os.path.exists(filename):
	os.remove(filename)

server_socket = socket(AF_INET,SOCK_DGRAM)
server_socket.setsockopt(SOL_SOCKET,SO_REUSEADDR, 1)
server_socket.bind(('',port))
print "Server is ready!!"
data_buff = {}
expected_seq = 0
while 1:
	while 1:
		'''write data buffer in file if matching'''
		if len(data_buff) != 0:
			if expected_seq in data_buff.keys():
				cur = expected_seq
				expected_seq = write_file(data_buff[cur],filename)
				del data_buff[cur]
			else:
				break
		else:	
			break
	try:
		server_socket.settimeout(5.0)
		message, client_address = server_socket.recvfrom(65535)
		if not message:
			break
	except timeout:
		print "Client is not sending..Exiting!!"		
		break
	random_num = gen_random_number()
	if random_num > probability:
		checksum = cal_checksum(message)
		if checksum == 1:
			if int(message[0:32],2) == expected_seq:
				send_msg = rdt_send(message)
				server_socket.sendto(send_msg, client_address)
				'''write to file'''
				expected_seq = write_file(message,filename)	
			elif int(message[0:32],2) > expected_seq:
				send_msg = rdt_send(message)
                                server_socket.sendto(send_msg, client_address)
				'''save in a buffer'''
				write_buff(message,data_buff)
			else:
				print "Ack retransmitted:" + str(int(message[0:32],2))
				send_msg = rdt_send(message)
				server_socket.sendto(send_msg, client_address)
		else:
			print "Packet Discarded, Checksum not matching!!!"
	else:
		checksum = cal_checksum(message)
                if checksum == 1:
			print "Packet Loss, sequence no:" + str(int(message[0:32],2))
		else:
			print "Packet Discarded, Checksum not matching!!!"

print "CLosed"
server_socket.close()