ssh -t pi@192.168.86.21 "rm -rf ~/client && mkdir client" && scp -r * pi@192.168.86.21:~/client/ && ssh -t pi@192.168.86.21 "cd client && python3 main.py"
