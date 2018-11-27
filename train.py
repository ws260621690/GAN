import tensorflow as tf
import numpy as np
import gen
import discr
import util


def train(img):
    """
    Function that generates the network and trains it using the data
    :param img: Dataset of images
    :return:
    """
    # define the batch size
    batch_size = 32

    """
    Define placeholders to feed the data
    """
    real = tf.placeholder(dtype=tf.float32, shape=[None, 128, 128, 3], name="data")
    fake = tf.placeholder(dtype=tf.float32, shape=[None, 1, 1, 128], name="latent")

    """
    Create first blocks for both the generator and the discriminator networks and train
    """
    g = gen.make(fake)
    d_fake = discr.make(g)
    d_real = discr.make(real)

    """
    Create the loss function
    """
    with tf.variable_scope("D_Loss"):
        d_loss_real = util.loss(logits=d_real, labels=tf.ones_like(d_real), name="Real")
        d_loss_fake = util.loss(logits=d_fake, labels=tf.zeros_like(d_fake), name="Fake")
        d_loss_op = tf.add(d_loss_real, d_loss_fake)

    g_loss_op = util.loss(logits=d_fake, labels=tf.ones_like(d_fake), name="G_Loss")

    """
    Create the optimizers that will minimize the loss function for D and maximize it for G
    """
    train_g = util.opt("G/Adam").minimize(g_loss_op, var_list=tf.get_collection("GEN_VAR"))
    train_d = util.opt("D/Adam").minimize(d_loss_op, var_list=tf.get_collection("DISCR_VAR"))

    """
    Create saver to store the trained weights
    """
    saver = tf.train.Saver()

    """
    Set up input for training
    """

    """
    Train the network
    """
    gen_loss = -np.inf
    discr_loss = np.inf
    with tf.Session() as sess:
        # initialize the GAN
        sess.run(tf.variables_initializer(tf.global_variables()))

        step = 1
        while True:
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

                # save checkpoint every 10 steps
                if step % 10 == 0:
                    saver.save(sess, "model/model.ckpt", global_step=step)

                if np.abs(gen_loss - gen_loss_) < 0.0001 or np.abs(discr_loss - discr_loss_) < 0.0001:
                    gen_loss, discr_loss = gen_loss_, discr_loss_
                    saver.save(sess, "model/trained_model.ckpt")
                    break
                else:
                    gen_loss, disct_loss = gen_loss_, discr_loss_
                    step += 1


if __name__ == "__main__":
    train(np.ones([150, 128, 128, 3]))