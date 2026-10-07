import json
import uuid
import boto3
from botocore.exceptions import ClientError

table = boto3.resource("dynamodb").Table("todos")

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}

def respond(status, body):
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body)}

def lambda_handler(event, context):
    # Set by the Cognito authorizer (added in a later step)
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    method = event["httpMethod"]
    todo_id = (event.get("pathParameters") or {}).get("id")
    body = json.loads(event.get("body") or "{}")

    try:
        if method == "POST":
            item = {
                "userId": user_id,
                "todoId": str(uuid.uuid4()),
                "title": body.get("title", ""),
                "done": False,
            }
            table.put_item(Item=item)
            return respond(201, item)

        if method == "GET":
            result = table.query(
                KeyConditionExpression="userId = :u",
                ExpressionAttributeValues={":u": user_id},
            )
            return respond(200, result["Items"])

        if method == "PUT" and todo_id:
            result = table.update_item(
                Key={"userId": user_id, "todoId": todo_id},
                UpdateExpression="SET title = :t, done = :d",
                ConditionExpression="attribute_exists(todoId)",
                ExpressionAttributeValues={
                    ":t": body.get("title", ""),
                    ":d": bool(body.get("done", False)),
                },
                ReturnValues="ALL_NEW",
            )
            return respond(200, result["Attributes"])

        if method == "DELETE" and todo_id:
            table.delete_item(
                Key={"userId": user_id, "todoId": todo_id},
                ConditionExpression="attribute_exists(todoId)",
            )
            return respond(200, {"deleted": todo_id})

        return respond(400, {"error": "Unsupported request"})

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return respond(404, {"error": "Todo not found"})
        return respond(500, {"error": "Server error"})
