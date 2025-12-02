install:
	sudo curl
	python3 -m venv .venv
	source .venv/bin/activate
	pip install --upgrade pip
	pip install -r requirements.txt

start:
	source .venv/bin/activate
	docker start mongodb_local
	uvicorn src.apis:app --host 0.0.0.0 --port 8000 --reload

run_train_nosql:
	curl -s -X POST http://0.0.0.0:8000/training | jq

run_predict_nosql:
	curl -s -X POST http://0.0.0.0:8000/predict   -H "Content-Type: application/json"   -d '{"designation":"shampoing enfant","description":"ne pique pas les yeux"}' | jq
