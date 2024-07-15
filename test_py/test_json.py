import json

with open('/home/pi/mu_code/info.json', 'r') as file:
    content = file.read()
    data = json.loads(content)   
with open('/home/pi/mu_code/info.json', 'w') as file:
    data['equipUuid'] = 'sdf'
    print(data)
    data = json.dumps(data)
    result = file.write(data)
    