#!/usr/bin/env python3
"""
Training script for custom NER model on Epstein-related entities.

This script generates synthetic training data with entities: FLIGHT_NUMBER, AIRCRAFT, FINANCIAL_INSTITUTION,
fine-tunes a spaCy model, evaluates it, and saves the model if F1 > 90%.
"""

import random
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

import spacy
from spacy.training import Example
from spacy.scorer import Scorer


def generate_entity_data() -> Tuple[List[str], List[str], List[str]]:
    """Generate lists of entity values."""
    airlines = ["AA", "BA", "UA", "DL", "LH", "AF", "KL"]
    flight_numbers = [f"{airline}{num}" for airline in airlines for num in range(100, 1000)]

    aircraft = [
        "Boeing 747", "Boeing 737", "Boeing 777", "Airbus A320", "Airbus A380",
        "Airbus A350", "Cessna Citation", "Gulfstream G650", "Bombardier Global Express"
    ]

    financial_institutions = [
        "Bank of America", "JPMorgan Chase", "Wells Fargo", "Citibank",
        "Goldman Sachs", "Morgan Stanley", "HSBC", "Deutsche Bank"
    ]

    return flight_numbers, aircraft, financial_institutions


def generate_training_data(num_examples: int = 2000) -> List[Tuple[str, Dict[str, Any]]]:
    """Generate synthetic training data."""
    flight_numbers, aircraft, financial_institutions = generate_entity_data()

    templates = [
        "Jeffrey Epstein flew on {FLIGHT_NUMBER} in his {AIRCRAFT}.",
        "The funds were transferred via {FINANCIAL_INSTITUTION}.",
        "Epstein used flight {FLIGHT_NUMBER} to travel to the island.",
        "He owned a {AIRCRAFT} registered to his company.",
        "Money laundering involved {FINANCIAL_INSTITUTION}.",
        "Flight {FLIGHT_NUMBER} was chartered for Epstein's associates.",
        "{AIRCRAFT} was spotted at Teterboro Airport.",
        "Transactions through {FINANCIAL_INSTITUTION} were flagged by regulators.",
        "Epstein boarded {FLIGHT_NUMBER} from Palm Beach.",
        "The {AIRCRAFT} belonged to Epstein's fleet.",
        "Suspicious activity at {FINANCIAL_INSTITUTION} linked to Epstein.",
        "Flight {FLIGHT_NUMBER} departed with Epstein aboard.",
        "Epstein's {AIRCRAFT} was used for trafficking.",
        "{FINANCIAL_INSTITUTION} accounts showed large transfers.",
    ]

    data = []
    for _ in range(num_examples):
        template = random.choice(templates)
        flight = random.choice(flight_numbers)
        air = random.choice(aircraft)
        fin = random.choice(financial_institutions)

        text = template.format(FLIGHT_NUMBER=flight, AIRCRAFT=air, FINANCIAL_INSTITUTION=fin)

        entities = []
        # Find positions
        if "{FLIGHT_NUMBER}" in template:
            start = text.find(flight)
            if start != -1:
                entities.append((start, start + len(flight), "FLIGHT_NUMBER"))
        if "{AIRCRAFT}" in template:
            start = text.find(air)
            if start != -1:
                entities.append((start, start + len(air), "AIRCRAFT"))
        if "{FINANCIAL_INSTITUTION}" in template:
            start = text.find(fin)
            if start != -1:
                entities.append((start, start + len(fin), "FINANCIAL_INSTITUTION"))

        annotations = {"entities": entities}
        data.append((text, annotations))

    return data


def split_data(data: List[Tuple[str, Dict[str, Any]]]) -> Tuple[List, List, List]:
    """Split data into train, dev, test."""
    random.shuffle(data)
    n = len(data)
    train_end = int(0.8 * n)
    dev_end = int(0.9 * n)
    train = data[:train_end]
    dev = data[train_end:dev_end]
    test = data[dev_end:]
    return train, dev, test


def train_model(train_data: List[Tuple[str, Dict[str, Any]]], dev_data: List[Tuple[str, Dict[str, Any]]], epochs: int = 20) -> spacy.Language:
    """Train the NER model."""
    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner", last=True)

    # Add labels
    for _, annotations in train_data:
        for ent in annotations["entities"]:
            ner.add_label(ent[2])

    # Begin training
    optimizer = nlp.begin_training()
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]

    for epoch in range(epochs):
        random.shuffle(train_data)
        losses = {}

        with nlp.disable_pipes(*other_pipes):
            for text, annotations in train_data:
                doc = nlp.make_doc(text)
                example = Example.from_dict(doc, annotations)
                nlp.update([example], losses=losses, sgd=optimizer)

        print(f"Epoch {epoch + 1}, Losses: {losses}")

        # Evaluate on dev
        scorer = Scorer()
        for text, annotations in dev_data[:100]:  # Sample for speed
            doc = nlp(text)
            example = Example.from_dict(doc, annotations)
            scorer.score([example])
        print(f"Dev F1: {scorer.scores['ents_f']:.2f}")

    return nlp


def evaluate_model(nlp: spacy.Language, test_data: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, float]:
    """Evaluate the model on test data."""
    scorer = Scorer()
    for text, annotations in test_data:
        doc = nlp(text)
        example = Example.from_dict(doc, annotations)
        scorer.score([example])
    return scorer.scores


def main():
    print("Generating training data...")
    data = generate_training_data(2000)
    train_data, dev_data, test_data = split_data(data)

    print(f"Train: {len(train_data)}, Dev: {len(dev_data)}, Test: {len(test_data)}")

    print("Training model...")
    nlp = train_model(train_data, dev_data, epochs=20)

    print("Evaluating model...")
    scores = evaluate_model(nlp, test_data)
    print(f"Test Scores: {scores}")

    f1 = scores.get("ents_f", 0)
    if f1 > 90:
        print(f"F1 score: {f1:.2f} > 90%, saving model...")
        model_path = Path("custom_epstein_ner_model")
        nlp.to_disk(model_path)
        print(f"Model saved to {model_path}")
    else:
        print(f"F1 score: {f1:.2f} < 90%, not saving.")


if __name__ == "__main__":
    main()