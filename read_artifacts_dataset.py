import datasets

dataset = datasets.load_dataset("tencent/ArtifactsBenchmark", split="train")

filtered = dataset.filter(lambda x: x["difficulty"] == "easy")

print(filtered[0])