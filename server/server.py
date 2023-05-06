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
from datetime import datetime, timezone

app = Flask(__name__)

app.config['SECRET_KEY'] = 'super-secret'
app.config['MONGO_URI'] = 'mongodb://rwuser:Singapore123!@190.92.206.138:27017,159.138.120.227:27017/test?authSource=admin'
bcrypt = Bcrypt(app)
def parse_json(data):
    return json.loads(json_util.dumps(data))
CORS(app)
CORS(app, origins=["http://localhost:3000"])
jwt = JWTManager(app)
# #### Setting up MongoDB ####
connection = 'mongodb://rwuser:Singapore123!@190.92.206.138:27017,159.138.120.227:27017/test?authSource=admin'
client = MongoClient(connection)
mydb = client.mydb


#### Retrieve Project ID
@app.route("/info", methods=['GET'])
@jwt_required()
def get_info():
    payload = get_jwt()
    employee_id = payload['EmployeeID']
    if mydb.Employee.find_one({'EmployeeID':employee_id}):
        # Retrieving Project IDS
        projects = mydb.EmployeeProjects.find({'EmployeeID':int(employee_id)})
        project_ids = []
        for project in projects:
            project_ids.append(project['ProjectID'])
        if len(project_ids) > 0:
            return jsonify({"ProjectIDs":project_ids})
        else:
            return {"message": "No Projects Found."}, 404 
    else:
        return  {"message": "Employee not found."}, 404       


#### Create Claim ####
@app.route("/create", methods=['POST'])
@jwt_required()
def create_claim():
    payload = get_jwt()
    content = request.json
    employee_id = payload["EmployeeID"]
    # firstname = content["FirstName"]
    # lastname = content["LastName"]
    project_id = content["ProjectID"]
    currency_id = content["CurrencyID"]
    expense_date = content["ExpenseDate"]
    amount = content["Amount"]
    purpose = content["Purpose"]
    chargeToDefault = content["ChargeToDefaultDept"]
    alternativeDeptCode = content["AlternativeDeptCode"]
    currency = mydb.Currency.find_one({"CurrencyID":currency_id})
    latest_claim = mydb.ProjectExpenseClaims.find().sort("ClaimID",-1).limit(1).next()
    print(latest_claim)
    latest_claim_id = str(int(latest_claim["ClaimID"]) + 1)
    print(latest_claim_id)
    timenow = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    new_doc = {
          "ClaimID": latest_claim_id,
          "ProjectID": project_id,
          "CurrencyID": currency_id,
          "EmployeeID": employee_id,
          "ExpenseDate": expense_date,
          "Amount": amount,
          "Purpose": purpose,
          "ChargeToDefaultDept": chargeToDefault,
          "AlternativeDeptCode": alternativeDeptCode,
          "Status": "Pending",
          "LastEditedClaimDate": timenow
    }
    
    mydb.ProjectExpenseClaims.insert_one(new_doc)
    return {"message":"Success"}, 200
    
    

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

#Update User
@app.route('/update',methods=['POST'])
@jwt_required()
def update():
    claims =get_jwt()
    employeeid = claims['EmployeeID']
    if mydb.ProjectExpenseClaim.find({"EmployeeID":employeeid}):
        firstname = request.json.get("FirstName")
        lastname = request.json.get("LastName")
        projectid = request.json.get("ProjectID")
        amount = request.json.get("Amount")
        purpose = request.json.get("Purpose")
        mydb.Employee.find_one_and_update(
            {"EmployeeID":employeeid},
            {"$set" : {"FirstName":firstname,"LastName":lastname}}
        )
        mydb.EmployeeProjects.find_one_and_update(
            {"EmployeeID":employeeid},
            {"$set" : {"ProjectID":projectid}}
        )
        mydb.ProjectExpenseClaims.find_one_and_update(
            {"EmployeeID":employeeid},
            {"$set" : {"Amount":amount,"Purpose":purpose}}
        )
        return {"message":"Claims have been updated."}
    return {"message":"User is not authorised."}


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

@app.route('/delete',methods=['DELETE'])
@jwt_required()
def delete_transaction():
    claims = get_jwt()
    employeeid = claims['EmployeeID']
    employeeCheck = parse_json(mydb.Employee.find({"EmployeeID":employeeid}))
    if employeeid == employeeCheck[0]['EmployeeID']:
        claims_data = request.get_json() #Claims_ID
        claimID = claims_data['ClaimID']
        if mydb.ProjectExpenseClaims.find({"ClaimID":claimID}):
            claimOutput = parse_json(mydb.ProjectExpenseClaims.find({"ClaimID":claimID}))
            db_claimID = claimOutput[0]['ClaimID']
            if claimID == db_claimID:
                delete_col = mydb['ProjectExpenseClaims']
                delete_col.delete_one(claims_data)
                return {"message":"Transaction has been deleted."}, 200    
    else:
        return {"message": "User is not authorised."}, 404
    return {"message":"Transaction ID cannot be found."}, 404


if __name__ == "__main__":
    app.run(debug=True)
