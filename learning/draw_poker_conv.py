import lasagne
import theano
import theano.tensor as T
import theano.printing as tp # theano.printing.pprint(variable) [tp.pprint(var)]
import time
import numpy as np

from poker_lib import *
from draw_poker import _load_poker_csv
from draw_poker import cards_input_from_string
from draw_poker import create_iter_functions
from draw_poker import train

DATA_FILENAME = '40000_full_sim_samples.csv' #'20000_full_sim_samples.csv'
# Not too much accuracy gain... in doubling the training data. And more than 2x as slow.
# '20000_full_sim_samples.csv' #'10000_A_full_sim_samples.csv' # 'mnist.pkl.gz'

MAX_INPUT_SIZE = 100000 # Remove this constraint, as needed
VALIDATION_SIZE = 1000
TEST_SIZE = 1000
NUM_EPOCHS = 50 # 20 # 20 # 100
BATCH_SIZE = 100 # 50 #100
NUM_HIDDEN_UNITS = 512 # 256 #512
# LEARNING_RATE = 0.02 # 0.01
# MOMENTUM = 0.9


def load_data():
    data = _load_poker_csv()

    X_all, y_all, z_all = data

    # Split into train (remainder), valid (1000), test (1000)
    X_split = np.split(X_all, [VALIDATION_SIZE, VALIDATION_SIZE + TEST_SIZE])
    X_valid = X_split[0]
    X_test = X_split[1]
    X_train = X_split[2]

    print('X_valid {} {}'.format(type(X_valid), X_valid.shape))
    print('X_test {} {}'.format(type(X_test), X_test.shape))
    print('X_train {} {}'.format(type(X_train), X_train.shape))

    # And same for Y
    y_split = np.split(y_all, [VALIDATION_SIZE, VALIDATION_SIZE + TEST_SIZE])
    y_valid = y_split[0]
    y_test = y_split[1]
    y_train = y_split[2]

    print('y_valid {} {}'.format(type(y_valid), y_valid.shape))
    print('y_test {} {}'.format(type(y_test), y_test.shape))
    print('y_train {} {}'.format(type(y_train), y_train.shape))

    #sys.exit(0)

    # We ignore validation & test for now.
    #X_valid, y_valid = data[1]
    #X_test, y_test = data[2]

    return dict(
        X_train=theano.shared(lasagne.utils.floatX(X_train)),
        y_train=T.cast(theano.shared(y_train), 'int32'),
        X_valid=theano.shared(lasagne.utils.floatX(X_valid)),
        y_valid=T.cast(theano.shared(y_valid), 'int32'),
        X_test=theano.shared(lasagne.utils.floatX(X_test)),
        y_test=T.cast(theano.shared(y_test), 'int32'),
        num_examples_train=X_train.shape[0],
        num_examples_valid=X_valid.shape[0],
        num_examples_test=X_test.shape[0],
        input_height=X_train.shape[2],
        input_width=X_train.shape[3],
        #input_dim=X_train.shape[1] * X_train.shape[2] * X_train.shape[3], # How much size per input?? 5x4x13 data (cards, suits, ranks)
        output_dim=32, # output cases
    )

def build_model(input_width, input_height, output_dim,
                batch_size=BATCH_SIZE):
    print('building model, layer by layer...')

    l_in = lasagne.layers.InputLayer(
        # Shape is *5* x width x height 
        shape=(batch_size, 5, input_width, input_height),
        )

    print('input layer shape %d x %d x %d x %d' % (batch_size, 5, input_width, input_height))

    l_conv1 = lasagne.layers.Conv2DLayer(
        l_in,
        num_filters=16, #16, #32,
        filter_size=(3,3), #(5,5), #(3,3), #(5, 5),
        nonlinearity=lasagne.nonlinearities.rectify,
        W=lasagne.init.GlorotUniform(),
        )

    # No hard rule that we need to pool after every 3x3!
    # l_pool1 = lasagne.layers.MaxPool2DLayer(l_conv1, ds=(2, 2))
    l_conv1_1 = lasagne.layers.Conv2DLayer(
        l_conv1,
        num_filters=16, #16, #32,
        filter_size=(3,3), #(5,5), #(3,3), #(5, 5),
        nonlinearity=lasagne.nonlinearities.rectify,
        W=lasagne.init.GlorotUniform(),
        )
    l_pool1 = lasagne.layers.MaxPool2DLayer(l_conv1_1, ds=(2, 2))

    # try 3rd conv layer
    #l_conv1_2 = lasagne.layers.Conv2DLayer(
    #    l_conv1_1,
    #    num_filters=16, #16, #32,
    #    filter_size=(3,3), #(5,5), #(3,3), #(5, 5),
    #    nonlinearity=lasagne.nonlinearities.rectify,
    #    W=lasagne.init.GlorotUniform(),
    #    )
    #l_pool1 = lasagne.layers.MaxPool2DLayer(l_conv1_2, ds=(2, 2))

    l_conv2 = lasagne.layers.Conv2DLayer(
        l_pool1,
        num_filters=32, #16, #32,
        filter_size=(3,3), #(5,5), # (3,3), #(5, 5),
        nonlinearity=lasagne.nonlinearities.rectify,
        W=lasagne.init.GlorotUniform(),
        )

    # Add 4th convolution layer...
    # l_pool2 = lasagne.layers.MaxPool2DLayer(l_conv2, ds=(2, 2))
    l_conv2_2 = lasagne.layers.Conv2DLayer(
        l_conv2,
        num_filters=32, #16, #32,
        filter_size=(3,3), #(5,5), # (3,3), #(5, 5),
        nonlinearity=lasagne.nonlinearities.rectify,
        W=lasagne.init.GlorotUniform(),
        )
    l_pool2 = lasagne.layers.MaxPool2DLayer(l_conv2_2, ds=(2, 2))

    # Add 3rd convolution layer!
    #l_conv3 = lasagne.layers.Conv2DLayer(
    #    l_pool2,
    #    num_filters=16, #16, #32,
    #    filter_size=(2,2), #(5,5), # (3,3), #(5, 5),
    #    nonlinearity=lasagne.nonlinearities.rectify,
    #    W=lasagne.init.GlorotUniform(),
    #    )
    #l_pool3 = lasagne.layers.MaxPool2DLayer(l_conv3, ds=(2, 2))

    l_hidden1 = lasagne.layers.DenseLayer(
        l_pool2, # l_pool3, # l_pool2,
        num_units=NUM_HIDDEN_UNITS,
        nonlinearity=lasagne.nonlinearities.rectify,
        W=lasagne.init.GlorotUniform(),
        )

    l_hidden1_dropout = lasagne.layers.DropoutLayer(l_hidden1, p=0.5)

    #l_hidden2 = lasagne.layers.DenseLayer(
    #     l_hidden1_dropout,
    #     num_units=NUM_HIDDEN_UNITS,
    #     nonlinearity=lasagne.nonlinearities.rectify,
    #     )
    #l_hidden2_dropout = lasagne.layers.DropoutLayer(l_hidden2, p=0.5)

    l_out = lasagne.layers.DenseLayer(
        l_hidden1_dropout, #l_hidden2_dropout, # l_hidden1_dropout,
        num_units=output_dim,
        nonlinearity=lasagne.nonlinearities.softmax,
        W=lasagne.init.GlorotUniform(),
        )

    return l_out

# Now how do I return theano function to predict, from my given thing? Should be simple.
def predict_model(output_layer, test_batch):
    print('Computing predictions on test_batch: {} {}'.format(type(test_batch), test_batch.shape))
    #pred = T.argmax(output_layer.get_output(test_batch, deterministic=True), axis=1)
    pred = output_layer.get_output(lasagne.utils.floatX(test_batch), deterministic=True)
    print('Prediciton: %s' % pred)
    #print(tp.pprint(pred))
    softmax_values = pred.eval()
    print(softmax_values)

    #f = theano.function([output_layer.get_output], test_batch)

    #print(f)

    #print('Predition eval: %' % pred.eval

    """
    pred = T.argmax(
        output_layer.get_output(X_batch, deterministic=True), axis=1)
    accuracy = T.mean(T.eq(pred, y_batch), dtype=theano.config.floatX)
    """

    pred_max = T.argmax(pred, axis=1)

    print('Maximums %s' % pred_max)
    #print(tp.pprint(pred_max))

    softmax_choices = pred_max.eval()
    print(softmax_choices)

    # now debug the softmax choices...
    softmax_debug = [DRAW_VALUE_KEYS[i] for i in softmax_choices]
    print(softmax_debug)



def main(num_epochs=NUM_EPOCHS):
    print("Loading data...")
    dataset = load_data()

    print("Building model and compiling functions...")
    output_layer = build_model(
        input_height=dataset['input_height'],
        input_width=dataset['input_width'],
        output_dim=dataset['output_dim'],
        )

    iter_funcs = create_iter_functions(
        dataset,
        output_layer,
        X_tensor_type=T.tensor4,
        )

    print("Starting training...")
    now = time.time()
    try:
        for epoch in train(iter_funcs, dataset):
            print("Epoch {} of {} took {:.3f}s".format(
                epoch['number'], num_epochs, time.time() - now))
            now = time.time()
            print("  training loss:\t\t{:.6f}".format(epoch['train_loss']))
            print("  validation loss:\t\t{:.6f}".format(epoch['valid_loss']))
            print("  validation accuracy:\t\t{:.2f} %%".format(
                epoch['valid_accuracy'] * 100))

            if epoch['number'] >= num_epochs:
                break

    except KeyboardInterrupt:
        pass

    # Can we do something with final output model? Like show a couple of moves...
    #test_batch = dataset['X_test']

    # Test cases -- it keeps the two aces. But can it recognize a straight? A flush? Trips? Draw?? Two pair??
    test_cases = ['As,Ad,4d,3s,2c', 'As,Ks,Qs,Js,Ts', '3h,3s,3d,5c,6d', '3h,4s,3d,5c,6d', '2h,3s,4d,6c,5s',
                  '8s,Ad,Kd,8c,Jd', '8s,Ad,2d,7c,Jd', '2d,7d,8d,9d,4d', '7c,8c,Tc,Js,Qh', '2c,8s,5h,8d,2s',
                  '[8s,9c,8c,Kd,7h]', '[Qh,3h,6c,5s,4s]', '[Jh,Td,9s,Ks,5s]', '[6c,4d,Ts,Jc,6s]', 
                  '[4h,8h,2c,7d,3h]', '[2c,Ac,Tc,6d,3d]', '[Ad,3c,Tc,4d,5d]'] 

    print('looking at some test cases: %s' % test_cases)

    # Fill in test cases to get to batch size?
    for i in range(BATCH_SIZE - len(test_cases)):
        test_cases.append(test_cases[1])
    test_batch = np.array([cards_input_from_string(case) for case in test_cases], np.int32)
    predict_model(output_layer=output_layer, test_batch=test_batch)

    print('again, the test cases: \n%s' % test_cases)

    #print(predict(output_layer[x=test_batch]))

    return output_layer


if __name__ == '__main__':
    main()
