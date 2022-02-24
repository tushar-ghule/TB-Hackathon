from datetime import datetime
from tqdm import tqdm


f = open('Crypto.txt','r')


lines = f.readlines()

size = len(lines)
count = 0

badOnes = []
for i in range(20):
    n = lines[i]
    row = n.split(',')
    if len(row) != 4:
        badOnes.append(n.split(','))
        count += 1
    print(datetime.fromtimestamp(float(row[3].rstrip('\n'))))
'''
print("Total: ",count)
for n in range(10):
    print(badOnes[n])

'''
