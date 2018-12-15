import numpy as np
import tensorflow as tf
import util


FLAGS = tf.flags.FLAGS

tf.flags.DEFINE_integer("batch_size", 100, "Defines the number of images per mini-batch")
tf.flags.DEFINE_bool("train", True, "Whether the network is trained or not")
tf.flags.DEFINE_string("img_path", "/tmp/celeba-128", "The path where to look for the images")
tf.flags.DEFINE_float("eps", float(np.finfo(np.float32).tiny), "Small number for batch_normalization")


def generator(inp):
    """
    Function that creates a generator network
    :param inp: Input to the network
    :return:
    """
    with tf.variable_scope("generator"):
        # define the first fully-connected layer
        lay = tf.layers.dense(inp, 1024, "sigmoid", name="layer_0")

        # define the first convolution layer 4x4
        lay = tf.layers.conv2d_transpose(inp, 512, 4, name="layer_1")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.nn.sigmoid(lay)

        # define the second layer 8x8
        lay = tf.layers.conv2d_transpose(lay, 256, 4, strides=2, padding="SAME", name="layer_2")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.nn.sigmoid(lay)

        # define the first layer 16x16
        lay = tf.layers.conv2d_transpose(lay, 128, 4, strides=2, padding="SAME", name="layer_3")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.nn.sigmoid(lay)

        # define the second layer 32x32
        lay = tf.layers.conv2d_transpose(lay, 3, 4, strides=2, padding="SAME", name="layer_4")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.nn.tanh(lay)

    return lay


def discriminator(inp, reuse):
    """
    Function that creates the discriminator network
    :param inp: Input to  the discriminator
    :param reuse: If the network reuses previously created weights or not
    :return:
    """
    with tf.variable_scope("discriminator", reuse=reuse):

        # define the second layer 16x16
        lay = tf.layers.conv2d(inp, 64, 4, strides=2, padding="SAME", name="layer_0")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.nn.sigmoid(lay)

        # define the third layer 8x8
        lay = tf.layers.conv2d(lay, 128, 4, strides=2, padding="SAME", name="layer_1")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.nn.sigmoid(lay)

        # define the third layer 4x4
        lay = tf.layers.conv2d(lay, 256, 4, strides=2, padding="SAME", name="layer_2")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.nn.sigmoid(lay)

        # define the first fully-connected layer
        lay = tf.layers.dense(inp, 1, "sigmoid", name="layer_3")
        lay = tf.nn.batch_normalization(lay, 0., 1., None, None, variance_epsilon=FLAGS.eps)
        lay = tf.squeeze(lay)

    return lay


def model(latent, real):
    """
    Function that creates the GAN by assembling the generator and the discriminator parts
    :param latent: Latent vector that serves as the input to the generator
    :param real: The real images
    :return:
    """
    g = generator(latent)
    d_real = discriminator(real, reuse=False)
    d_fake = discriminator(g, reuse=True)

    # define the generator loss
    g_loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.ones_like(d_fake), logits=d_fake)
    g_loss = tf.reduce_mean(g_loss)

    # define the discriminator loss
    d_loss_real = tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.ones_like(d_real), logits=d_real)
    d_loss_real = tf.reduce_mean(d_loss_real)
    d_loss_fake = tf.nn.sigmoid_cross_entropy_with_logits(labels=tf.zeros_like(d_fake), logits=d_fake)
    d_loss_fake = tf.reduce_mean(d_loss_fake)

    return g_loss, d_loss_real + d_loss_fake


def train():
    """
    Function that trains the network
    :return:
    """
    img = util.load_img(FLAGS.img_path, [32, 32])
    fake = tf.placeholder(dtype=tf.float32, shape=[FLAGS.batch_size, 1, 1, 128], name="latent")
    real = tf.placeholder(dtype=tf.float32, shape=[FLAGS.batch_size, 32, 32, 3], name="real")
    g_loss_op, d_loss_op = model(fake, real)

    # Optimizers for the generator and the discriminator
    train_g = tf.train.RMSPropOptimizer(5e-3).minimize(g_loss_op)
    train_d = tf.train.RMSPropOptimizer(5e-3).minimize(d_loss_op)

    # add summary scalars
    tf.summary.scalar("discriminator loss", d_loss_op)
    tf.summary.scalar("generator loss", g_loss_op)
    merged = tf.summary.merge_all()

    # savers to save the trained weights for the generator and the discriminator
    g_saver = tf.train.Saver(tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope="generator"))
    d_saver = tf.train.Saver(tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope="discriminator"))

    # train the network
    gen_loss = np.inf
    discr_loss = np.inf
    with tf.Session() as sess:
        # create writer for summaries
        writer = tf.summary.FileWriter("debug", sess.graph)

        # initialize the GAN
        sess.run(tf.variables_initializer(tf.global_variables()))

        step = 1
        while True:
            g_batch_loss = np.empty([0, ])
            d_batch_loss = np.empty([0, ])
            for i in np.arange(np.ceil(img.shape[0] / FLAGS.batch_size), dtype=np.int32):
                min_ = FLAGS.batch_size * i
                max_ = np.minimum(min_ + FLAGS.batch_size, img.shape[0])

                batch = img[min_:max_, :, :, :]

                # generate images
                gen_img = np.random.normal(loc=0., scale=1., size=[FLAGS.batch_size, 1, 1, 128])

                # train the discriminator on the fake images
                _, discr_loss_ = sess.run([train_d, d_loss_op], feed_dict={real: batch, fake: gen_img})

                # train the generator to fool discriminator
                _, gen_loss_ = sess.run([train_g, g_loss_op], feed_dict={fake: gen_img})

                g_batch_loss = np.append(g_batch_loss, gen_loss_)
                d_batch_loss = np.append(d_batch_loss, discr_loss_)

            print("Step ", step)
            print("Generator loss is: ", np.mean(g_batch_loss))
            print("Discriminator loss is: ", np.mean(d_batch_loss), "\n")

            # save checkpoint every 10 steps and print to terminal
            if step % 10 or step == 1.:
                summary = sess.run(merged,
                                   feed_dict={
                                       real: img,
                                       fake: np.random.normal(loc=0., scale=1., size=[img.shape[0], 1, 1, 128])})
                writer.add_summary(summary, step)
                g_saver.save(sess, "model/model.ckpt", global_step=step - 1)

            if step > 1000:  # np.abs(gen_loss - np.mean(g_batch_loss)) < 0.0001:
                gen_loss, discr_loss = np.mean(g_batch_loss), np.mean(d_batch_loss)
                g_saver.save(sess, "model/g_weights.ckpt")
                d_saver.save(sess, "model/d_weights.ckpt")
                break
            else:
                gen_loss, discr_loss = np.mean(g_batch_loss), np.mean(d_batch_loss)
                step += 1


if __name__ == "__main__":
    train()
