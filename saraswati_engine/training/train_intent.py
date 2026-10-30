#!/usr/bin/env python3
import json
import random
import re
import unicodedata
from pathlib import Path
from collections import Counter

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

SEED = 42
random.seed(SEED)
torch.manual_seed(SEED)

TRAIN_DATA = {
    "list_files": [
        "show me files", "list files", "show files in this folder",
        "list the files in current directory", "what files are here",
        "display directory contents", "show directory contents",
        "open file list", "files please", "find the files in this folder",
        "files dikhao", "file dikhao", "folder ke files dikhao",
        "is folder mein kya files hain", "directory ke files dikhao",
        "फाइलें दिखाओ", "फाइल्स दिखाओ", "इस फोल्डर की फाइलें दिखाओ",
        "डायरेक्टरी में कौन सी फाइलें हैं", "फाइलों की सूची दिखाओ",
        "files dakhva", "file dakhva", "files dakhwa",
        "folder madhle files dakhva", "ya folder madhle files dakhva",
        "ithe kontya files aahet", "directory madhle files dakhva",
        "फाइल दाखवा", "फाईल दाखवा", "फोल्डरमधील फाईल्स दाखवा",
        "या फोल्डरमध्ये कोणत्या फाईल्स आहेत", "फाईल्सची यादी दाखवा",
    ],
    "show_user": [
        "who am i", "what is my username", "show my username",
        "which user is logged in", "tell me the current user",
        "who is logged into this computer", "display my user name",
        "what account am i using", "my login name",
        "main kaun hoon", "mera username kya hai", "mera user name batao",
        "abhi kaun login hai", "computer par kaun login hai",
        "मैं कौन हूँ", "मेरा यूजरनेम क्या है", "मेरा नाम बताओ",
        "अभी कौन लॉगिन है", "कौन सा यूजर लॉगिन है",
        "mi kon ahe", "mi kon aahe", "maza username kay ahe",
        "atta kon login ahe", "computer var kon login ahe",
        "मी कोण आहे", "माझं युजरनेम काय आहे", "माझे युजरनेम सांगा",
        "सध्या कोण लॉगिन आहे", "कॉम्प्युटरवर कोण लॉगिन आहे",
    ],
    "show_date": [
        "what is today's date", "show the date", "what time is it",
        "current date and time", "tell me today's date and time",
        "display current time", "what is the current time",
        "give me the date", "date please", "tell me the time now",
        "aaj ki taarikh kya hai", "abhi kitne baje hain",
        "aaj ki date batao", "date aur time batao", "samay kya hua hai",
        "आज की तारीख क्या है", "अभी कितने बजे हैं", "आज की तारीख बताओ",
        "समय और तारीख बताओ", "अभी का समय क्या है",
        "aajchi tarik kay ahe", "atta kiti vajle", "aajchi date sang",
        "vel ani tarikh sang", "atta vel kay ahe",
        "आजची तारीख काय आहे", "आत्ता किती वाजले", "आजची तारीख सांगा",
        "वेळ आणि तारीख सांगा", "आत्ताची वेळ काय आहे",
    ],
    "system_uptime": [
        "system uptime", "how long has the computer been on",
        "show system uptime", "how long has my PC been running",
        "how long since startup", "time since boot", "check computer uptime",
        "is my computer running for a long time", "show boot duration",
        "system kitne time se on hai", "computer kitni der se chalu hai",
        "pc kab se chalu hai", "uptime batao", "system kitni der se chal raha hai",
        "कंप्यूटर कितनी देर से चालू है", "सिस्टम कितनी देर से चल रहा है",
        "अपटाइम बताओ", "कंप्यूटर कब से चालू है", "सिस्टम का अपटाइम दिखाओ",
        "system kiti vel chalu ahe", "computer kiti vel chalu aahe",
        "pc kevha pasun chalu ahe", "uptime dakhva", "system kiti vel chalu aahe",
        "कॉम्प्युटर किती वेळ चालू आहे", "सिस्टम किती वेळ सुरू आहे",
        "सिस्टमचा अपटाइम दाखवा", "पीसी केव्हापासून चालू आहे",
    ],
    "os_info": [
        "operating system info", "show operating system information",
        "what operating system am i using", "show kernel version",
        "which Linux version is installed", "system information",
        "display kernel details", "tell me about my OS",
        "linux version kya hai", "mera operating system batao",
        "kernel version dikhao", "system ki jankari do", "kaunsa Linux hai",
        "ऑपरेटिंग सिस्टम की जानकारी दो", "लिनक्स का वर्जन क्या है",
        "कर्नेल वर्जन दिखाओ", "मेरे सिस्टम की जानकारी दो",
        "sistim chi mahiti dya", "linux chi version kay ahe",
        "kernel version dakhva", "mazi operating system konti ahe",
        "system chi mahiti sang", "linux konta ahe",
        "सिस्टीमची माहिती द्या", "लिनक्सची आवृत्ती कोणती आहे",
        "कर्नल व्हर्जन दाखवा", "माझी ऑपरेटिंग सिस्टम कोणती आहे",
    ],
    "disk_space": [
        "check disk space", "how much storage is left", "storage status",
        "disk usage", "free space", "show available storage",
        "disk space dikhao", "storage kitni baki hai", "hard disk ki jankari do",
        "डिस्क स्पेस दिखाओ", "स्टोरेज कितनी बची है", "हार्ड डिस्क की जानकारी दो",
        "disk space dakhva", "storage kiti ahe", "hard disk chi mahiti dya",
        "डिस्क स्पेस दाखवा", "स्टोरेज किती बाकी आहे", "हार्ड डिस्कची माहिती द्या",
    ],
    "process_management": [
        "show running processes", "list running apps", "process list",
        "what processes are running", "show active tasks",
        "running processes dikhao", "kaunse processes chal rahe hain",
        "चल रही प्रक्रियाएं दिखाओ", "प्रोसेस लिस्ट दिखाओ",
        "running processes dakhva", "process kase baghave",
        "चालू प्रोसेसेस दाखवा", "प्रक्रियांची यादी दाखवा",
    ],
    "launch_app": [
        "open vs code", "launch vscode", "open firefox", "start browser",
        "open vlc", "start code editor", "open terminal",
        "vs code kholo", "firefox chalu karo", "browser open karo",
        "वीएस कोड खोलो", "फायरफॉक्स चालू करो", "ब्राउज़र खोलो",
        "vs code ughada", "firefox suru kar", "browser dakhv",
        "व्हीएस कोड उघडा", "फायरफॉक्स सुरू करा",
    ],
}

INTENTS = sorted(TRAIN_DATA.keys())
INTENT_MAP = {i: label for i, label in enumerate(INTENTS)}
REVERSE_INTENT_MAP = {label: i for i, label in INTENT_MAP.items()}

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text)

def build_vocab(data):
    vocab = {}
    for phrase, _label in data:
        for token in normalize(phrase).split():
            if token not in vocab:
                vocab[token] = len(vocab)
    return vocab

def text_to_vector(text, vocab):
    vector = torch.zeros(len(vocab), dtype=torch.float32)
    for token in normalize(text).split():
        idx = vocab.get(token)
        if idx is not None:
            vector[idx] = 1.0
    return vector

class IntentClassifierNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.layer1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.layer2 = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        return self.layer2(self.relu(self.layer1(x)))

def main():
    examples = []
    seen = set()
    for label, phrases in TRAIN_DATA.items():
        for phrase in phrases:
            key = (normalize(phrase), label)
            if key not in seen:
                examples.append((phrase, label))
                seen.add(key)

    vocab = build_vocab(examples)
    x_train = torch.stack([text_to_vector(text, vocab) for text, _ in examples])
    y_train = torch.tensor(
        [REVERSE_INTENT_MAP[label] for _, label in examples],
        dtype=torch.long,
    )

    hidden_size = 64
    model = IntentClassifierNN(len(vocab), hidden_size, len(INTENTS))
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    dataset = TensorDataset(x_train, y_train)
    loader = DataLoader(dataset, batch_size=16, shuffle=True)

    epochs = 350
    model.train()
    for epoch in range(epochs):
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            loss = criterion(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()

    # Save directly to saraswati_engine/models/
    model_dir = Path(__file__).resolve().parent.parent / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "saraswati_intent_model.pth"
    vocab_path = model_dir / "vocab.json"

    torch.save(
        {
            "model_state": model.state_dict(),
            "input_size": len(vocab),
            "hidden_size": hidden_size,
            "output_size": len(INTENTS),
            "intent_map": INTENT_MAP,
        },
        model_path,
    )
    with vocab_path.open("w", encoding="utf-8") as f:
        json.dump(vocab, f, ensure_ascii=False, indent=2)

    print(f"Training complete! Model saved to: {model_path}")

if __name__ == "__main__":
    main()