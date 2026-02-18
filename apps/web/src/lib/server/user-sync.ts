import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient, UpdateCommand } from "@aws-sdk/lib-dynamodb";

type Claims = {
  sub: string;
  email?: string;
  name?: string;
  "cognito:username"?: string;
};

const tableName = process.env.DYNAMODB_TABLE_USERS?.trim();
const region = process.env.COGNITO_REGION?.trim() || process.env.AWS_REGION?.trim() || "us-east-2";

const ddb = DynamoDBDocumentClient.from(
  new DynamoDBClient({
    region,
  }),
  {
    marshallOptions: {
      removeUndefinedValues: true,
    },
  },
);

export async function upsertUserProfileFromClaims(claims: Claims) {
  if (!tableName) {
    throw new Error("Missing DYNAMODB_TABLE_USERS env var");
  }

  if (!claims.sub) {
    throw new Error("JWT is missing sub claim");
  }

  const now = new Date().toISOString();
  const email = claims.email || "";
  const name = claims.name || claims["cognito:username"] || email || claims.sub;

  await ddb.send(
    new UpdateCommand({
      TableName: tableName,
      Key: {
        sub: claims.sub,
      },
      UpdateExpression:
        "SET email = :email, #name = :name, lastLogin = :lastLogin, createdAt = if_not_exists(createdAt, :createdAt)",
      ExpressionAttributeNames: {
        "#name": "name",
      },
      ExpressionAttributeValues: {
        ":email": email,
        ":name": name,
        ":lastLogin": now,
        ":createdAt": now,
      },
    }),
  );

  return {
    sub: claims.sub,
    email,
    name,
    lastLogin: now,
  };
}
