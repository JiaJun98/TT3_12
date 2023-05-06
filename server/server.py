from flask import Flask,jsonify, request
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import json
from bson import json_util
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_jwt
from flask_cors import CORS

app = Flask(__name__)

app.config['SECRET_KEY'] = 'super-secret'
app.config['MONGO_URI'] = 'mongodb://rwuser:Singapore123!@190.92.206.138:27017,159.138.120.227:27017/test?authSource=admin'
bcrypt = Bcrypt(app)
def parse_json(data):
    return json.loads(json_util.dumps(data))
CORS(app)
jwt = JWTManager(app)
# #### Setting up MongoDB ####
connection = 'mongodb://rwuser:Singapore123!@190.92.206.138:27017,159.138.120.227:27017/test?authSource=admin'
client = MongoClient(connection)
mydb = client.mydb

#User Log in 
@app.route("/login", methods=["POST"])
def login():
    employeeid = request.json.get("EmployeeID", None)
    password = request.json.get("Password", None)
    employee = mydb.Employee.find({"EmployeeID":employeeid})
    hash_password = bcrypt.generate_password_hash(password,10)
    if employee and bcrypt.check_password_hash(hash_password,parse_json(employee)[0]['Password']):
        additional_claims = {"EmployeeID": parse_json(mydb.Employee.find({"EmployeeID":employeeid}))[0]['EmployeeID']}
        access_token = create_access_token(identity=employeeid,additional_claims=additional_claims)
        return jsonify(access_token=access_token)
    return jsonify({"msg": "Bad username or password"}), 401

# Retrieve claim record list of an employee
@app.route('/claim',methods=['GET'])
@jwt_required()
def get_claim_records():
    jwt_claims = get_jwt()
    employeeId = jwt_claims['EmployeeID']
    if mydb.Employee.find({"EmployeeID":employeeId}) and mydb.ProjectExpenseClaims.find({"EmployeeID":employeeId}):
        if mydb.ProjectExpenseClaims.find({"EmployeeID":employeeId}):
            claims = mydb.ProjectExpenseClaims.find({"EmployeeID": employeeId})
            claim_records = []
            for claim in claims:
                claim_record = {
                    "ClaimID": claim["ClaimID"],
                    "ProjectID": claim["ProjectID"],
                    "CurrencyID": claim["CurrencyID"],
                    "Amount": claim["Amount"],
                    "Status": claim["Status"]
                }
                claim_records.append(claim_record)
            return claim_records
    else:
        return {"message": "User is not authorised."}, 404
    return {"message": "Employee not found."}, 404

if __name__ == "__main__":
    app.run(debug=True)
