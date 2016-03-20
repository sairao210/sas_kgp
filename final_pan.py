import math
import numpy as np
import cv2
from numpy import linalg

def resize(a,width):
    img = cv2.imread(a)

    r = 2000.0/img.shape[1]
    dim = (2000,int(img.shape[0]*r))

    img2 = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)

    #cv2.imwrite('rcam3.jpg',img2)
    return img2


def findDimensions(image, homography):
    base_p1 = np.ones(3, np.float32)
    base_p2 = np.ones(3, np.float32)
    base_p3 = np.ones(3, np.float32)
    base_p4 = np.ones(3, np.float32)

    (y, x) = image.shape[:2]

    base_p1[:2] = [0,0]
    base_p2[:2] = [x,0]
    base_p3[:2] = [0,y]
    base_p4[:2] = [x,y]

    max_x = None
    max_y = None
    min_x = None
    min_y = None

    for pt in [base_p1, base_p2, base_p3, base_p4]:

        hp = np.matrix(homography, np.float32) * np.matrix(pt, np.float32).T

        hp_arr = np.array(hp, np.float32)

        normal_pt = np.array([hp_arr[0]/hp_arr[2], hp_arr[1]/hp_arr[2]], np.float32)

        if ( max_x == None or normal_pt[0,0] > max_x ):
            max_x = normal_pt[0,0]

        if ( max_y == None or normal_pt[1,0] > max_y ):
            max_y = normal_pt[1,0]

        if ( min_x == None or normal_pt[0,0] < min_x ):
            min_x = normal_pt[0,0]

        if ( min_y == None or normal_pt[1,0] < min_y ):
            min_y = normal_pt[1,0]

    min_x = min(0, min_x)
    min_y = min(0, min_y)

    return (min_x, min_y, max_x, max_y)

def filter_matches(matches, ratio = 0.75):
    filtered_matches = []
    for m in matches:
        if len(m) == 2 and m[0].distance < m[1].distance * ratio:
            filtered_matches.append(m[0])
    
    return filtered_matches

def tmpst(base_img_rgb,next_img_rgb):
    #base_img_rgb = cv2.imread(a)
    base_img = cv2.GaussianBlur(cv2.cvtColor(base_img_rgb,cv2.COLOR_BGR2GRAY), (5,5), 0)

    detector = cv2.SURF()
    base_features, base_descs = detector.detectAndCompute(base_img, None)

    #next_img_rgb = cv2.imread(b)
    next_img = cv2.GaussianBlur(cv2.cvtColor(next_img_rgb,cv2.COLOR_BGR2GRAY), (5,5), 0)

    next_features, next_descs = detector.detectAndCompute(next_img, None)

    FLANN_INDEX_KDTREE = 1  # bug: flann enums are missing
    flann_params = dict(algorithm = FLANN_INDEX_KDTREE, 
        trees = 5)
    matcher = cv2.FlannBasedMatcher(flann_params, {})
    matches = matcher.knnMatch(next_descs, trainDescriptors=base_descs, k=2)
    matches_subset = filter_matches(matches)

    kp1 = []
    kp2 = []
    for match in matches_subset:
        kp1.append(base_features[match.trainIdx])
        kp2.append(next_features[match.queryIdx])
    p1 = np.array([k.pt for k in kp1])
    p2 = np.array([k.pt for k in kp2])

    H, status = cv2.findHomography(p1, p2, cv2.RANSAC, 5.0)
    inlierRatio = float(np.sum(status)) / float(len(status))

    H = H / H[2,2]
    H_inv = linalg.inv(H)

    if ( inlierRatio > 0.1 ): # and 

        (min_x, min_y, max_x, max_y) = findDimensions(next_img, H_inv)

    # Adjust max_x and max_y by base img size
        max_x = max(max_x, base_img.shape[1])
        max_y = max(max_y, base_img.shape[0])

        move_h = np.matrix(np.identity(3), np.float32)

        if ( min_x < 0 ):
            move_h[0,2] += -min_x
            max_x += -min_x

        if ( min_y < 0 ):
            move_h[1,2] += -min_y
            max_y += -min_y

        #print "Homography: \n", H
        #print "Inverse Homography: \n", H_inv
        #print "Min Points: ", (min_x, min_y)

        mod_inv_h = move_h * H_inv

        img_w = int(math.ceil(max_x))
        img_h = int(math.ceil(max_y))

        #print "New Dimensions: ", (img_w, img_h)

            # Warp the new image given the homography from the old image
        base_img_warp = cv2.warpPerspective(base_img_rgb, move_h, (img_w, img_h))
        #print "Warped base image"

            # utils.showImage(base_img_warp, scale=(0.2, 0.2), timeout=5000)
            # cv2.destroyAllWindows()

        next_img_warp = cv2.warpPerspective(next_img_rgb, mod_inv_h, (img_w, img_h))
        #print "Warped next image"

        # utils.showImage(next_img_warp, scale=(0.2, 0.2), timeout=5000)
        # cv2.destroyAllWindows()

        # Put the base image on an enlarged palette
        enlarged_base_img = np.zeros((img_h, img_w, 3), np.uint8)

        #print "Enlarged Image Shape: ", enlarged_base_img.shape
        #print "Base Image Shape: ", base_img_rgb.shape
        #print "Base Image Warp Shape: ", base_img_warp.shape

        # enlarged_base_img[y:y+base_img_rgb.shape[0],x:x+base_img_rgb.shape[1]] = base_img_rgb
        # enlarged_base_img[:base_img_warp.shape[0],:base_img_warp.shape[1]] = base_img_warp

        # Create a mask from the warped image for constructing masked composite
        (ret,data_map) = cv2.threshold(cv2.cvtColor(next_img_warp, cv2.COLOR_BGR2GRAY), 
            0, 255, cv2.THRESH_BINARY)

        enlarged_base_img = cv2.add(enlarged_base_img, base_img_warp, 
            mask=np.bitwise_not(data_map), 
            dtype=cv2.CV_8U)

        # Now add the warped image
        final_img = cv2.add(enlarged_base_img, next_img_warp, 
            dtype=cv2.CV_8U)

    else:
        final_img = base_img_rgb

    return final_img


def stitch(a,b,c):
    a = resize(a,2000)
    b = resize(b,2000)
    c = resize(c,2000)
    
    t = tmpst(b,c)
    ans = tmpst(t,a)

    return ans
    


ans = stitch('/Python27/panaroma/1.jpg','/Python27/panaroma/2.jpg','/Python27/panaroma/3.jpg')
cv2.imwrite('final_ans_test23.jpg',ans)

















    
    
        
