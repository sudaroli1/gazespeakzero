"""
Build and validate e3/intent_bank.json.

Every object must exist in the E2 AAC vocabulary (aac_vocab.py), so that E2's
output and E3's input are the same vocabulary. Run:

    python build_intent_bank.py            # writes intent_bank.json and prints checks
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "study2_scene_vocabulary"))
from aac_vocab import AAC_VOCAB, canon  # noqa: E402

# purpose: needs | information | social | etiquette   (Light 1988)
# source: the published category the intent comes from (see E3_DESIGN.md)
B = [
    # ---------------- wants and needs (33) ----------------
    ("bedroom", "needs", "board:thirst", ["water_bottle", "straw_(for_drinking)"],
     "I am thirsty, can I have some water?",
     ["Could I have a drink of water, please?", "I would like water with a straw."]),
    ("bedroom", "needs", "board:medication", ["pill", "water_bottle"],
     "It is time for my medicine, please bring it with water.",
     ["Can I have my tablet with some water?", "My pills are due now."]),
    ("bedroom", "needs", "board:temperature", ["blanket"],
     "I am cold, can I have another blanket?",
     ["Please put another blanket over me.", "I feel cold, I need a blanket."]),
    ("bedroom", "needs", "board:temperature", ["fan"],
     "I am too warm, please turn on the fan.",
     ["Could you switch the fan on? It is hot.", "Please put the fan on for me."]),
    ("bedroom", "needs", "board:position", ["pillow"],
     "Please move my pillow, my head is uncomfortable.",
     ["Can you fix my pillow?", "My pillow needs adjusting."]),
    ("bedroom", "needs", "board:position", ["bed", "quilt", "pillow"],
     "Please straighten my bed covers.",
     ["The quilt needs pulling up.", "Could you tidy my bedding?"]),
    ("bedroom", "needs", "board:toileting", ["toilet"],
     "I need to use the toilet.",
     ["Please take me to the toilet.", "I have to go to the bathroom."]),
    ("bedroom", "needs", "board:secretions", ["tissue_paper"],
     "I need a tissue, please.",
     ["Could you pass me a tissue?", "Please wipe my mouth with a tissue."]),
    ("bedroom", "needs", "board:sleep", ["lamp"],
     "Please turn the light off, I want to sleep.",
     ["Switch the lamp off, I am tired.", "Turn off the bedside light, please."]),
    ("bedroom", "needs", "board:vision", ["spectacles"],
     "Can you pass me my glasses?",
     ["I need my spectacles.", "Please put my glasses on for me."]),
    ("bedroom", "needs", "board:mobility", ["walking_stick"],
     "Pass me my walking stick, I want to move.",
     ["I need my stick.", "Bring me my walking cane, please."]),
    ("bedroom", "needs", "board:dressing", ["sock", "slipper_(footwear)", "shoe"],
     "Please put my socks and slippers on.",
     ["I want my socks and slippers.", "Could you dress my feet?"]),
    ("bathroom", "needs", "board:hygiene", ["toothbrush", "toothpaste", "cup"],
     "I want to brush my teeth.",
     ["Please help me clean my teeth.", "Bring my toothbrush and toothpaste."]),
    ("bathroom", "needs", "board:hygiene", ["shower_head", "towel", "soap"],
     "I would like a shower now.",
     ["Please help me wash in the shower.", "I want to be showered."]),
    ("bathroom", "needs", "board:toileting", ["toilet_tissue"],
     "The toilet paper is finished, please bring more.",
     ["We need more toilet roll.", "There is no toilet paper left."]),
    ("bathroom", "needs", "board:hygiene", ["soap", "sink"],
     "I want to wash my hands.",
     ["Please help me wash my hands with soap.", "Can I clean my hands at the sink?"]),
    ("bathroom", "needs", "board:grooming", ["hairbrush"],
     "Please brush my hair.",
     ["Could you do my hair?", "I would like my hair brushed."]),
    ("bathroom", "needs", "board:grooming", ["mirror"],
     "Hold the mirror up, I want to see myself.",
     ["Let me look in the mirror.", "Please show me my face in the mirror."]),
    ("kitchen", "needs", "board:thirst", ["kettle", "mug"],
     "I would like a hot drink, please.",
     ["Could you make me a cup of tea?", "Please boil the kettle for me."]),
    ("kitchen", "needs", "board:thirst", ["milk", "glass_(drink_container)"],
     "Can I have a glass of milk?",
     ["I would like some milk.", "Please pour me milk in a glass."]),
    ("kitchen", "needs", "board:hunger", ["sandwich"],
     "I am hungry, I would like a sandwich.",
     ["Could you make me a sandwich?", "I want something to eat, a sandwich."]),
    ("kitchen", "needs", "board:thirst", ["refrigerator", "orange_juice"],
     "There is juice in the fridge, can I have some?",
     ["Please get the orange juice from the fridge.", "I would like juice, it is in the refrigerator."]),
    ("kitchen", "needs", "board:medication", ["medicine", "spoon"],
     "My liquid medicine is due, please give it to me.",
     ["Bring my medicine and a spoon.", "It is time for my syrup."]),
    ("dining", "needs", "board:hunger", ["plate", "fork", "napkin"],
     "I am ready to eat now.",
     ["Please bring my meal.", "I would like my food."]),
    ("dining", "needs", "board:thirst", ["cup", "straw_(for_drinking)"],
     "Can I have a drink with a straw?",
     ["Please give me my cup with a straw.", "I need a straw for my drink."]),
    ("dining", "needs", "board:hygiene", ["napkin"],
     "I need a napkin, please.",
     ["Could you pass me a serviette?", "Please wipe my mouth with a napkin."]),
    ("dining", "needs", "board:feeding", ["spoon"],
     "Please feed me with a spoon, it is easier.",
     ["Use the spoon to feed me.", "I would rather be fed with a spoon."]),
    ("living room", "needs", "board:entertainment", ["television_set", "remote_control"],
     "Please turn on the television.",
     ["Switch the TV on for me.", "I want to watch television."]),
    ("living room", "needs", "board:position", ["sofa", "cushion"],
     "I want to sit on the sofa.",
     ["Please move me to the couch.", "Help me onto the sofa with a cushion."]),
    ("living room", "needs", "board:mobility", ["wheelchair"],
     "I want to get into my wheelchair.",
     ["Please transfer me to the wheelchair.", "Put me in my chair with wheels."]),
    ("living room", "needs", "board:light", ["curtain"],
     "Please open the curtains.",
     ["Could you draw the curtains back?", "I want to see outside, open the curtain."]),
    ("living room", "needs", "board:temperature", ["heater"],
     "Please turn up the heater.",
     ["It is cold, put the heating on.", "Could you increase the heater?"]),
    ("bedroom", "needs", "board:comfort", ["hand_towel"],
     "My face is sweaty, please wipe it with a towel.",
     ["Could you dab my forehead with a towel?", "Please use a towel on my face."]),
    # ---------------- information exchange (10) ----------------
    ("bedroom", "information", "info:time", ["alarm_clock"],
     "What time is it?",
     ["Could you tell me the time?", "Is it morning already?"]),
    ("living room", "information", "info:schedule", ["wall_clock"],
     "When is my appointment today?",
     ["What time do we leave for the clinic?", "Tell me the time of my appointment."]),
    ("bedroom", "information", "info:medical", ["medicine"],
     "I have already taken my medicine.",
     ["My tablets are done for now.", "Do not give me the medicine again."]),
    ("bedroom", "information", "info:instruction", ["notebook", "pen"],
     "Write this down for me, please.",
     ["Take a note of this.", "Please use the notebook to write it."]),
    ("living room", "information", "info:instruction", ["laptop_computer"],
     "Open my laptop, I want to check my email.",
     ["Please start the computer for me.", "I need my laptop to read messages."]),
    ("bedroom", "information", "info:entertainment", ["book"],
     "Read me the next chapter of my book.",
     ["Please continue my book.", "Read to me from that book."]),
    ("living room", "information", "info:news", ["newspaper"],
     "Read me the news, please.",
     ["What does the paper say today?", "Tell me the headlines from the newspaper."]),
    ("kitchen", "information", "info:safety", ["stove"],
     "Be careful, the stove is still on.",
     ["Turn the cooker off, it is burning.", "The gas is still lit."]),
    ("bedroom", "information", "info:maintenance", ["table_lamp"],
     "The lamp beside my bed is not working.",
     ["My bedside light is broken.", "That lamp needs a new bulb."]),
    ("dining", "information", "info:household", ["cake"],
     "There is cake for the visitors, offer them some.",
     ["Give our guests some cake.", "The cake is for everybody."]),
    # ---------------- social closeness (10) ----------------
    ("bedroom", "social", "social:family", ["cellular_telephone"],
     "Call my family, I want to talk to them.",
     ["Please phone my daughter.", "I would like to speak to my family on the phone."]),
    ("living room", "social", "social:conversation", ["painting"],
     "That painting is my favourite, tell me about it.",
     ["I like looking at that picture.", "Talk to me about the painting."]),
    ("living room", "social", "social:pets", ["dog"],
     "Bring the dog to me, I want to stroke it.",
     ["Let the dog come up here.", "I want to pet the dog."]),
    ("bedroom", "social", "social:pets", ["cat"],
     "Is the cat here? I would like to see her.",
     ["Bring the cat in, please.", "Where is my cat?"]),
    ("living room", "social", "social:conversation", ["flower_arrangement"],
     "Who sent these flowers?",
     ["Tell me who brought the flowers.", "Where did that bouquet come from?"]),
    ("dining", "social", "social:celebration", ["wineglass"],
     "Pour me a little wine, let us celebrate.",
     ["A small glass of wine for me too.", "I would like to join the toast."]),
    ("living room", "social", "social:music", ["radio_receiver"],
     "Put some music on, please.",
     ["Turn the radio on.", "I would like to listen to music."]),
    ("bedroom", "social", "social:conversation", ["magazine"],
     "Sit with me and look at this magazine.",
     ["Let us go through the magazine together.", "Stay and read the magazine with me."]),
    ("living room", "social", "social:company", ["armchair"],
     "Sit down next to me for a while.",
     ["Take the armchair and stay with me.", "Please keep me company here."]),
    ("bedroom", "social", "social:music", ["headset"],
     "Put my headphones on, I want to listen.",
     ["Help me with my headset.", "I would like my headphones."]),
    # ---------------- social etiquette (7) ----------------
    ("dining", "etiquette", "etiquette:thanks", ["plate"],
     "That was lovely, thank you.",
     ["The meal was very good, thank you.", "Thank you for my food."]),
    ("living room", "etiquette", "etiquette:offer", ["cup", "teapot", "milk"],
     "Would you like a cup of tea?",
     ["Have some tea with me.", "Shall we offer our guest tea?"]),
    ("dining", "etiquette", "etiquette:welcome", ["chair"],
     "Please sit down, make yourself comfortable.",
     ["Take a seat, please.", "Do sit down with us."]),
    ("bedroom", "etiquette", "etiquette:thanks", ["flower_arrangement"],
     "Thank you for the flowers, they are beautiful.",
     ["It was kind of you to bring flowers.", "The flowers are lovely, thank you."]),
    ("living room", "etiquette", "etiquette:apology", ["television_set"],
     "Sorry, could you turn the television down?",
     ["The TV is a little loud, sorry.", "Please lower the television volume."]),
    ("dining", "etiquette", "etiquette:apology", ["napkin", "table"],
     "Excuse me, I have spilled something on the table.",
     ["Sorry, I have made a mess here.", "I need help, I spilt my drink."]),
    ("bedroom", "etiquette", "etiquette:welcome", ["chair", "bed"],
     "Please come in and sit down beside me.",
     ["Bring a chair over and sit with me.", "You are welcome, sit here."]),
]


def main():
    bank, bad = [], []
    for i, (room, purpose, source, objs, utt, paras) in enumerate(B, 1):
        for o in objs:
            if o not in AAC_VOCAB:
                bad.append((i, o))
        bank.append({"id": f"I{i:02d}", "room": room, "purpose": purpose, "source": source,
                     "objects": [canon(o) for o in objs], "objects_raw": objs,
                     "utterance": utt, "paraphrases": paras})
    if bad:
        raise SystemExit(f"objects not in the AAC vocabulary: {bad}")
    out = os.path.join(HERE, "intent_bank.json")
    json.dump(bank, open(out, "w"), indent=1)

    from collections import Counter
    first = Counter(b["objects"][0] for b in bank)
    shared = sum(v for v in first.values() if v > 1)
    print(f"{len(bank)} intents -> {out}")
    print("purposes:", dict(Counter(b['purpose'] for b in bank)))
    print("rooms:", dict(Counter(b['room'] for b in bank)))
    print("object-list lengths:", dict(Counter(len(b['objects']) for b in bank)))
    print(f"intents sharing their first object with another intent: {shared}")
    print("duplicate utterances:", [u for u, c in Counter(b['utterance'] for b in bank).items() if c > 1])
    assert len({b["utterance"] for b in bank}) == len(bank), "duplicate utterance"


if __name__ == "__main__":
    main()
