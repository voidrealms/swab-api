Bare bone Charles Swab API client
Likely will not develop this further, part of a larger project.

Wanted to share in case it helps anyone :)

In the charles swab portal, get your application key and secret.
Paste them into the script.

If you get a 404 error, its likely because you need to go into the swab portal and authorize your application to access that part of the api.

Note this will translate the old TDA symbols to Swab symbols ($SPX.X = $SPX)

Usage:
```
client = Client()
client.setup() #every 7 days
qoute = client.get_Qoute('$SPX.X')
chain = client.get_Option('$SPX.X',datetime.now())
```
