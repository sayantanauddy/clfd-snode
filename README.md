# Stable Continual Learning from Demonstration
This repository contains the code and datasets for our paper **Scalable and Efﬁcient Continual Learning from Demonstration via a Hypernetwork-generated Stable Dynamics Model** ([preprint](https://arxiv.org/abs/2311.03600)).

## Overview
We propose a novel hypernetwork-based approach for stable continual learning from demonstration, enabling a robot to sequentially acquire multiple trajectory-based stable motion skills with a single hypernetwork without retraining on previous demonstrations. The stability in learned trajectories not only prevents divergence in motion but also greatly enhances continual learning performance, particularly in our most size-efficient model. We propose an efficient hypernetwork training method and provide new datasets for the LfD community. Evaluations on various benchmarks, including real-world robotic manipulation tasks, validate our approach.

<p style="text-align:center">
  <img src="images/clfd_snode_intro.svg" width="800" /> 
  <figcaption>
  Fig 1: Overview of key results and our proposed approach:<br/>
    (a) Continual learning from demonstration with stable NODEs generated by a chunked hypernetwork outperforms NODE-based continual learning by a wide margin.<br/>
    (b) Stochastic regularization with a single regularization term (CHN-1) performs as well as the fully regularized model (CHN-all) on real-world tasks but results in much more efficient training.<br/>
    (c) Architecture of a CHN-sNODE model: a chunked hypernetwork (CHN) generates the parameters of a stable NODE comprising a nominal dynamics model and a Lyapunov function.<br/>
    (d) Illustrations of the 9 real-world tasks of our proposed RoboTasks9 dataset. The last 5 tasks are introduced in our current paper. 
    With our proposed approach, all tasks can be learned in a continual manner with a single hypernetwork model without retraining on past demonstrations, with minimal forgetting, and with stability in the predicted trajectories.
  </figcaption>
</p>

<p style="text-align:center">
  <img src="images/clfd_snode_pred_all_1024.gif" width="800" /> 
  <figcaption>Fig 2: After continually learning the 9 real-world tasks of the RoboTasks9 dataset with a single CHN-sNODE model, the robot is able to perform any of the past tasks accurately (each task involves changing positions and orientations).</figcaption>
</p>

Here is a short video overview of our approach:

<video width="1920" width="1080"  src="https://github.com/sayantanauddy/clfd-snode/assets/10401716/1958249e-5cab-4ae3-887b-2a7c6f2da0b6"></video>

## Datasets

### High-dimensional LASA
The LASA 2D, 8D, 16D and 32D datasets used in our experiments can be found in `datasets/LASA` in the form of `.npy` files.

### RoboTasks9
The RoboTasks9 dataset can be found in `datasets/robottasks/pos_ori`.

## Acknowledgements

We gratefully acknowlege these openly accessible repositories which were a great help in writing the code for our experiments:

1. [Continual Learning with Hypernetworks](https://github.com/chrhenning/hypercl)
2. [Learning Stable Deep Dynamics Models](https://github.com/locuslab/stable_dynamics)
3. [Notebook](https://colab.research.google.com/drive/1ygdXFuih_0sLA2HosQkaVQOA9v6BMSdj?usp=sharing) containing starter code for Neural ODEs by Çağatay Yıldız
4. [Fast implementations of the Frechet distance](https://github.com/joaofig/discrete-frechet)

## Citation

If you use our code, dataset or our results in your research, please cite:

```
@misc{auddy2024scalable,
      title={Scalable and Efficient Continual Learning from Demonstration via a Hypernetwork-generated Stable Dynamics Model}, 
      author={Sayantan Auddy and Jakob Hollenstein and Matteo Saveriano and Antonio Rodríguez-Sánchez and Justus Piater},
      year={2024},
      eprint={2311.03600},
      archivePrefix={arXiv},
      primaryClass={cs.RO}
}
```
