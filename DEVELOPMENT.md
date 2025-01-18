# Development

## Workspace

Install dependencies and create venv:

```sh
brew install python
python3 -m venv .venv
.venv/bin/pip3 install -r requirements.txt -r requirements.dev.txt
echo "PYTHONPATH=.venv/lib" > .env # for vs code
```
