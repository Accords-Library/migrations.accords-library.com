from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport


# STEP 1: SETUP

urlGraphQL = ""
accessToken = ""

with open(".env.local", "r") as configFile:
    for line in configFile.readlines():
        if line.startswith("URL_GRAPHQL="):
            urlGraphQL = line[len("URL_GRAPHQL="):-1]
        elif line.startswith("ACCESS_TOKEN="):
            accessToken = line[len("ACCESS_TOKEN="):-1]


# Select your transport with a defined url endpoint
transport = AIOHTTPTransport(url=urlGraphQL, headers={
                             'Authorization': "Bearer " + accessToken})

# Create a GraphQL client using the defined transport
client = Client(transport=transport, fetch_schema_from_transport=True)

# Provide a GraphQL query
migrationContentsIds = gql(
    """
    query migrationContentsIds {
      contents(pagination: { limit: -1 }) {
        data {
          id
        }
      }
    }
    """
)

mutation = gql(
    """
  mutation updateContent($id: ID!, $data: ContentInput!) {
    updateContent(id: $id, data: $data) {
      data {
        id
      }
    }
  }
  """
)

migrationContent = gql(
    """
  query migrationContent($id: ID!) {
    content(id: $id) {
      data {
        attributes {
          titles {
            language {
              data {
                id
              }
            }
            pre_title
            title
            subtitle
            description
          }
          text_set {
            language {
              data {
                id
              }
            }
            status
            source_language {
              data {
                id
              }
            }
            transcribers {
              data {
                id
              }
            }
            translators {
              data {
                id
              }
            }
            proofreaders {
              data {
                id
              }
            }
            notes
            text
          }
        }
      }
    }
  }
  """
)


# STEP 2: GET LIST OF IDS

# Execute the query on the transport
ids = client.execute(migrationContentsIds)["contents"]["data"]
ids = [id["id"] for id in ids]


for id in ids:
    # STEP 3: GET DATA FROM SPECIFIC ID
    content = client.execute(migrationContent, variable_values={"id": id})[
        "content"]["data"]["attributes"]

    # STEP 4: TRANSFORM DATA
    newContent = {}
    for title in content["titles"]:
        langid = title["language"]["data"]["id"]
        newContent[langid] = {}
        newContent[langid]["language"] = langid
        newContent[langid]["pre_title"] = title["pre_title"]
        newContent[langid]["title"] = title["title"]
        newContent[langid]["subtitle"] = title["subtitle"]
        newContent[langid]["description"] = title["description"]

    for textSet in content["text_set"]:
        langid = textSet["language"]["data"]["id"]
        if langid not in newContent:
            newContent[langid] = {}
            newContent[langid]["language"] = langid
            newContent[langid]["title"] = "MISSING TITLE"
        newContent[langid]["text_set"] = {}
        newContent[langid]["text_set"]["status"] = textSet["status"]
        newContent[langid]["text_set"]["source_language"] = textSet["source_language"]["data"]["id"]
        newContent[langid]["text_set"]["text"] = textSet["text"]
        newContent[langid]["text_set"]["transcribers"] = [e["id"]
                                                          for e in textSet["transcribers"]["data"]]
        newContent[langid]["text_set"]["translators"] = [e["id"]
                                                         for e in textSet["translators"]["data"]]
        newContent[langid]["text_set"]["proofreaders"] = [e["id"]
                                                          for e in textSet["proofreaders"]["data"]]
        newContent[langid]["text_set"]["notes"] = textSet["notes"]

    # STEP 5: UPDATE ON THE CMS

    client.execute(mutation, variable_values={"id": id,
                                              "data": {
                                                  "translations": [newContent[e] for e in newContent]
                                              }})
