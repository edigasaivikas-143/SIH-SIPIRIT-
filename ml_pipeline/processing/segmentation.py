import torch
import torch.nn as nn
import torch.nn.functional as F

class ToyPointNet(nn.Module):
    def __init__(self, num_classes=3): # e.g., Wall, Floor, Common Space
        super().__init__()
        self.conv1 = nn.Conv1d(3, 64, 1)
        self.conv2 = nn.Conv1d(64, 128, 1)
        self.conv3 = nn.Conv1d(128, 1024, 1)
        self.fc1 = nn.Linear(1024, 512)
        self.fc2 = nn.Linear(512, 256)
        self.fc3 = nn.Linear(256, num_classes)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = F.relu(self.conv3(x))
        x = torch.max(x, 2, keepdim=True)[0] # Max pooling
        x = x.view(-1, 1024)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

def classify_points(point_cloud_tensor):
    model = ToyPointNet()
    model.eval()
    with torch.no_grad():
        return model(point_cloud_tensor)
