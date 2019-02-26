#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: zcy
# @Date:   2019-02-24 10:14:04
# @Last Modified by:   zcy
# @Last Modified time: 2019-02-24 12:53:24
import math, cv2
from skimage import io
import numpy as np
import sys, os

class SLIC:
    def __init__(self, img, mask, step):
        self.img = img
        self.mask = mask
        self.height, self.width = img.shape[:2]
        # self._convertToLAB()
        self.labimg = np.copy(self.img)
        self.step = step
        self.nc = 2
        self.ns = 30
        self.FLT_MAX = 1000000
        self.ITERATIONS = 10

    def generateSuperPixels(self):
        self._initData()
        indnp = np.mgrid[0:self.height,0:self.width].swapaxes(0,2).swapaxes(0,1)
        for i in range(self.ITERATIONS):
            self.distances = self.FLT_MAX * np.ones(self.img.shape[:2])
            # do not compute on background
            self.distances[self.mask==0]=0
            for j in range(self.centers.shape[0]):
                xlow, xhigh = int(self.centers[j][1] - self.step), int(self.centers[j][1] + self.step)
                ylow, yhigh = int(self.centers[j][2] - self.step), int(self.centers[j][2] + self.step)

                if xlow <= 0:
                    xlow = 0
                if xhigh > self.width:
                    xhigh = self.width
                if ylow <=0:
                    ylow = 0
                if yhigh > self.height:
                    yhigh = self.height

                cropimg = self.labimg[ylow : yhigh , xlow : xhigh]
                colordiff = cropimg - self.labimg[int(self.centers[j][2]), int(self.centers[j][1])]
                colorDist =np.square(colordiff)


                yy, xx = np.ogrid[ylow : yhigh, xlow : xhigh]
                pixdist = ((yy-self.centers[j][2])**2 + (xx-self.centers[j][1])**2)**0.5
                dist = (colorDist/self.nc)**2 + (pixdist/self.ns)**2

                distanceCrop = self.distances[ylow : yhigh, xlow : xhigh]

                idx = dist < distanceCrop
                distanceCrop[idx] = dist[idx]
                self.distances[ylow : yhigh, xlow : xhigh] = distanceCrop
                self.clusters[ylow : yhigh, xlow : xhigh][idx] = j

            for k in range(len(self.centers)):
                idx = (self.clusters == k)
                colornp = self.labimg[idx]
                distnp = indnp[idx]
                self.centers[k][0:1] = np.sum(colornp, axis=0)
                sumy, sumx = np.sum(distnp, axis=0)
                self.centers[k][1:] = sumx, sumy
                for ind in range(len(self.centers[k])):
                    if np.sum(idx)==0:
                        self.centers[k][ind]=0
                    else:
                        self.centers[k][ind] /= np.sum(idx)

    def _initData(self):
        self.clusters = -1 * np.ones(self.img.shape[:2])
        self.distances = self.FLT_MAX * np.ones(self.img.shape[:2])
        self.distances[self.mask==0]=0

        centers = []
        for i in range(self.step, int(self.width - self.step/2), self.step):
            for j in range(self.step, int(self.height - self.step/2), self.step):
                
                nc = self._findLocalMinimum(center=(i, j))
                color = self.labimg[nc[1], nc[0]]
                center = [color, nc[0], nc[1]]
                centers.append(center)
        self.center_counts = np.zeros(len(centers))
        self.centers = np.array(centers)

    def createConnectivity(self):
        label = 0
        adjlabel = 0
        lims = int(self.width * self.height / self.centers.shape[0])
        dx4 = [-1, 0, 1, 0]
        dy4 = [0, -1, 0, 1]
        new_clusters = -1 * np.ones(self.img.shape[:2]).astype(np.int64)
        elements = []
        for i in range(self.width):
            for j in range(self.height):
                if new_clusters[j, i] == -1:
                    elements = []
                    elements.append((j, i))
                    for dx, dy in zip(dx4, dy4):
                        x = elements[0][1] + dx
                        y = elements[0][0] + dy
                        if (x>=0 and x < self.width and 
                            y>=0 and y < self.height and 
                            new_clusters[y, x] >=0):
                            adjlabel = new_clusters[y, x]
                count = 1
                c = 0
                while c < count:
                    for dx, dy in zip(dx4, dy4):
                        x = elements[c][1] + dx
                        y = elements[c][0] + dy

                        if (x>=0 and x<self.width and y>=0 and y<self.height):
                            if new_clusters[y, x] == -1 and self.clusters[j, i] == self.clusters[y, x]:
                                elements.append((y, x))
                                new_clusters[y, x] = label
                                count+=1
                    c+=1
                if (count <= lims*0.2):
                    for c in range(count):
                        new_clusters[elements[c]] = adjlabel
                    label-=1
                label+=1
        self.clusters = new_clusters

    def displayContours(self, color):
        dx8 = [-1, -1, 0, 1, 1, 1, 0, -1]
        dy8 = [0, -1, -1, -1, 0, 1, 1, 1]

        isTaken = np.zeros(self.img.shape[:2], np.bool)
        contours = []

        for i in range(self.width):
            for j in range(self.height):
                nr_p = 0
                for dx, dy in zip(dx8, dy8):
                    x = i + dx
                    y = j + dy
                    if x>=0 and x < self.width and y>=0 and y < self.height:
                        if isTaken[y, x] == False and self.clusters[j, i] != self.clusters[y, x]:
                            nr_p += 1

                if nr_p >= 2:
                    isTaken[j, i] = True
                    contours.append([j, i])

        img_show = self.img.copy().astype(np.uint8)
        img_BGR = cv2.cvtColor(img_show, cv2.COLOR_GRAY2BGR)
        for i in range(len(contours)):
            img_BGR[contours[i][0], contours[i][1]] = (0, 0, 255)
        return img_BGR

    def _findLocalMinimum(self, center):
        min_grad = self.FLT_MAX
        loc_min = center
        for i in range(center[0] - 1, center[0] + 2):
            for j in range(center[1] - 1, center[1] + 2):
                c1 = self.labimg[j+1, i]
                c2 = self.labimg[j, i+1]
                c3 = self.labimg[j, i]
                if ((c1 - c3)**2)**0.5 + ((c2 - c3)**2)**0.5 < min_grad:
                    min_grad = abs(c1 - c3) + abs(c2 - c3)
                    loc_min = [i, j]
        return loc_min

def mk_dir(path):
    if not os.path.exists(os.path.join(path)):
        os.makedirs(os.path.join(path))

def spx_img(img, mask, nr_superpixels):
    step = int((img.shape[0]*img.shape[1]/nr_superpixels)**0.5)
    slic = SLIC(img, mask, step)
    slic.generateSuperPixels()
    slic.createConnectivity()
    img_show = slic.displayContours(color=255)
    return img_show

def spx_folder(in_dir, out_dir, nr_superpixels):
    mk_dir(out_dir)
    files = [f for f in os.listdir(in_dir) if '.png' in f and 'maxseg' not in f]
    files.sort()
    masks = np.load(os.path.join(in_dir, 'seg.npy'))
    for i, file in enumerate(files):
        img = io.imread(os.path.join(in_dir, file)).astype(np.float32)
        mask = masks[i]
        img_show = spx_img(img, mask, nr_superpixels)
        file = file.replace('.png', 'spx.png')
        cv2.imwrite(os.path.join(out_dir, file), img_show)
    return 


def process_dataset(datafolder, new_datafolder, nr_superpixels):
    mk_dir(new_datafolder)
    folder_list = os.listdir(datafolder)
    cnt = 0

    for folder in folder_list:
        cnt += 1
        old_folder = os.path.join(datafolder, folder)
        new_folder = os.path.join(new_datafolder, folder)
        print(str(cnt)+" : convert data from"+old_folder+"\n  to"+new_folder)
        spx_folder(old_folder, new_folder, nr_superpixels)

        if cnt>4: break
        if cnt%100==0: print("{}/{}".format(cnt, len(folder_list)))



if __name__ == '__main__':

    process_dataset('./res_data', './spx_set', 200)