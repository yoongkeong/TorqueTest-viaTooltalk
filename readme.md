when program starts
begin tooltalk connection check with controller (default is MT6000)
if connection is present, proceed next step:

1. user define how many screw holes to be evaluate (remark for user: if 10 screw holes, will be A,B,C...J)
2. user define how many samples to be evaluated
3. user to upload image of the placement of the screw holes, first ask how many image.
   1. if 1 image, all screw holes should be presented there, if 2 images were input, ask user how many screwhole at each image.
4. After user able to upload the image, the image should store under lib folder
5. then depends on the input of the screw holes number, generate alphabatic boxes e.g. A,B,C,D,E,F.. to allow user to drag and drop at the placement of the screw hole at the images user uploaded. (Ensure all screw holes are included and all alphatic boxes should be place as an indicator at the image user uploaded, then saved the arranged/edited image which will be used by the program to instruct user)
6. Upon completion of above, ask user to proceed start test.
7. once started, ask user which torque setting should be set, default 24Ncm-1
8. after set the torque, begin test:
   1. show image N (first arranged image saved), and record the torque of the screwdriver by Ncm per second, saved as A (First torque result)
   2. proceed next, B, and the placement of B at image sequence (if more than 1 image)
   3. proceed the rest until the screw holes user defined has finished.
9. Upon saving all results (which should be in csv format "A default sample format output by tooltalk controller), generate a plot which plot all samples in a plot
10. Present the plot at the end of the plot as well as a prompt to show image saved to /results folder.
11. Repeat above steps 7-10 depending on step 2 how many samples to be evaluated by user
