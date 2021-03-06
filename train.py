import tensorflow as tf
import numpy as np
import gen
import discr
import util
import sys


def train(img):
    """
    Function that generates the network and trains it using the data
    :param img: Dataset of images
    :return:
    """
    # define the batch size
    batch_size = 100

    """
    Define placeholders to feed the data
    """
    real = tf.placeholder(dtype=tf.float32, shape=[None, 128, 128, 3], name="data")
    fake = tf.placeholder(dtype=tf.float32, shape=[None, 1, 1, 128], name="latent")

    """
    Create first blocks for both the generator and the discriminator networks and train
    """
    g = gen.make(fake)
    g = tf.nn.tanh(g) # puts images in the [-1, 1] range
    d_real = discr.make(real, reuse=False)
    d_fake = discr.make(g, reuse=True)


    """
    Create the loss function
    """
    with tf.variable_scope("D_Loss"):
        d_loss_op = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
            labels=tf.ones_like(d_real),
            logits=d_real)
        ) + \
                    tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
                        labels=tf.zeros_like(d_fake),
                        logits=d_fake))

    with tf.variable_scope("G_Loss"):
        g_loss_op = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(
            labels=tf.ones_like(d_fake),
            logits=d_fake))

    """
    Add summary operations for each loss
    """
    tf.summary.scalar("D_Loss", d_loss_op)
    tf.summary.scalar("G_Loss", g_loss_op)
    merged = tf.summary.merge_all()

    """
    Create the optimizers that will minimize the loss function for D and G
    """
    train_g = tf.train.RMSPropOptimizer(5e-5).minimize(g_loss_op,
                                                       var_list=tf.get_collection(
                                                           tf.GraphKeys.TRAINABLE_VARIABLES,
                                                       scope="G"))

    train_d = tf.train.RMSPropOptimizer(5e-5).minimize(d_loss_op,
                                                       var_list=tf.get_collection(
                                                           tf.GraphKeys.TRAINABLE_VARIABLES,
                                                       scope="D"))

    """
    Create saver to store the trained weights
    """
    saver = tf.train.Saver(tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope="G"))

    """
    Train the network
    """
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
            for i in np.arange(np.ceil(img.shape[0] / batch_size), dtype=np.int32):
                min_ = batch_size * i
                max_ = np.minimum(min_ + batch_size, img.shape[0])

                batch = img[min_:max_, :, :, :]

                # generate images
                gen_img = np.random.normal(loc=0., scale=1., size=[batch_size, 1, 1, 128])

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
                saver.save(sess, "model/model.ckpt", global_step=step-1)

            if step > 400:# np.abs(gen_loss - np.mean(g_batch_loss)) < 0.0001:
                gen_loss, discr_loss = np.mean(g_batch_loss), np.mean(d_batch_loss)
                saver.save(sess, "model/trained_model.ckpt")
                break
            else:
                gen_loss, discr_loss = np.mean(g_batch_loss), np.mean(d_batch_loss)
                step += 1


if __name__ == "__main__":
    args = sys.argv
    # Set up input for training
    data = util.load_img(args[1], [128, 128])
    data = (data - 127.5) / 127.5
    train(data)