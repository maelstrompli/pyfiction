import argparse
import logging

from keras.optimizers import RMSprop
from keras.utils import plot_model
from pyfiction.agents.lstm_agent import LSTMAgent
from pyfiction.simulators.games.catsimulator2016_simulator import CatSimulator2016Simulator
from pyfiction.simulators.games.machineofdeath_simulator import MachineOfDeathSimulator
from pyfiction.simulators.games.savingjohn_simulator import SavingJohnSimulator
from pyfiction.simulators.games.starcourt_simulator import StarCourtSimulator
from pyfiction.simulators.games.theredhair_simulator import TheRedHairSimulator
from pyfiction.simulators.games.transit_simulator import TransitSimulator
from pyfiction.simulators.text_games.simulators.MySimulator import StoryNode

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

"""
An LSTM agent that supports leave-one-out generalisation testing
"""

simulators = [CatSimulator2016Simulator(),
              MachineOfDeathSimulator(),
              SavingJohnSimulator(),
              StarCourtSimulator(),
              TheRedHairSimulator(),
              TransitSimulator()]

parser = argparse.ArgumentParser()
parser.add_argument('--simulator',
                    help='index of a simulator to use for leave-one-out testing [1-6], 0 for training and testing all',
                    type=int,
                    default=0)

args = parser.parse_args()
simulator_index = args.simulator

if simulator_index == 0:
    train_simulators = simulators
    test_simulators = simulators
    print('Training and testing on all games:', [simulator.game.name for simulator in simulators])
else:
    train_simulators = simulators[:simulator_index - 1] + simulators[simulator_index:]
    test_simulators = simulators[simulator_index - 1]
    print('Training on games:', [simulator.game.name for simulator in train_simulators])
    print('Testing on game:', test_simulators.game.name)

# Create the agent and specify maximum lengths of descriptions (in words)
agent = LSTMAgent(train_simulators=train_simulators, test_simulators=test_simulators)

# Load or learn the vocabulary (random sampling on this many games could be extremely slow)
agent.initialize_tokens('vocabulary.txt')

optimizer = RMSprop(lr=0.00001)

embedding_dimensions = 16
lstm_dimensions = 32
dense_dimensions = 8

agent.create_model(embedding_dimensions=embedding_dimensions,
                   lstm_dimensions=lstm_dimensions,
                   dense_dimensions=dense_dimensions,
                   optimizer=optimizer)

# Visualize the model
try:
    plot_model(agent.model, to_file='model.png', show_shapes=True)
except ImportError as e:
    logger.warning("Couldn't print the model image: {}".format(e))

# Iteratively train the agent on a batch of previously seen examples while continuously expanding the experience buffer
# This example seems to ...
epochs = 1
for i in range(epochs):
    logger.info('Epoch %s', i)
    agent.train_online(episodes=8192, batch_size=256, gamma=0.95, epsilon=1, epsilon_decay=0.999,
                       prioritized_fraction=0.25, test_interval=16, test_steps=5, log_prefix=str(simulator_index))

# train the agent on the tested game
if simulator_index != 0:
    agent.clear_experience()
    agent.train_simulators = test_simulators if isinstance(test_simulators, list) else [test_simulators]
    agent.train_online(episodes=8192, batch_size=256, gamma=0.95, epsilon=1, epsilon_decay=0.999,
                       prioritized_fraction=0.25, test_interval=16, test_steps=5, log_prefix=str(simulator_index))
