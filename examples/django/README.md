
## Django StarWars Example
This is a simple StarWars demo Django GraphQL application with Inigo middleware.

#### How to run
1. Install python dependencies
```bash
pip3 install -r requirements.txt
```
2. Create an Inigo service and token at [app.inigo.io](https://app.inigo.io)
> Note: For this example name your service ***django_starwars***
3. Place the token into the **.env** file
4. Start the StarWars app
```bash
python3 app.py runserver 8080
```
5. Use the [playground](http://127.0.0.1:8080/query) to send some GraphQL requests.
6. Login to [Inigo](https://app.inigo.io) to see your requests

#### Initial service configuration
1. Install the Inigo [CLI](https://docs.inigo.io/cli/installation)
2. Apply the provided sample configuration
```bash
inigo apply config/service.yaml
```
> Note: This configuration file assumes the service name is ***django_starwars***. If you used a different name, edit the service.yaml file with the name of the service you created.

#### Simple security configuration
1. Have a look at the sample config/security.yaml file. This sets some simple configurations like requiring operation name, max depth of 3 and a few others.
2. Apply the provided sample security configuration
```bash
inigo apply config/security.yaml
```
3. Try sending an anonymous request that doesn't have operation name such as:
```graphql
query {
	films {
		title
	}
}
```
4. Try sending a nested query:
```graphql
query Pilots {
  films {
    vehicles {
      pilotedBy {
        name
      }
    }
  }
}
```

#### Docs
For many more security features such as access control, rate limiting and more, see the [docs](https://docs.inigo.io)

#### Support
Join our [slack](https:/slack.inigo.io/)

##### Helpful Hint
To dump your schema to a file run:
```bash
python3 app.py graphql_schema --schema schema.schema --out schema.graphql
```