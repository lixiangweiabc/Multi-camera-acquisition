# -- coding: utf-8 --
import threading
import msvcrt
import numpy as np
import time
import sys, os
import datetime
import inspect
import ctypes
import random
from ctypes import *

from CameraParams_header import *
from MvCameraControl_class import *

# 强制关闭线程
def Async_raise(tid, exctype):
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


# 停止线程
def Stop_thread(thread):
    Async_raise(thread.ident, SystemExit)


# 转为16进制字符串
def To_hex_str(num):
    chaDic = {10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f'}
    hexStr = ""
    if num < 0:
        num = num + 2 ** 32
    while num >= 16:
        digit = num % 16
        hexStr = chaDic.get(digit, str(digit)) + hexStr
        num //= 16
    hexStr = chaDic.get(num, str(num)) + hexStr
    return hexStr


# 是否是Mono图像,单色图像
def Is_mono_data(enGvspPixelType):
    if PixelType_Gvsp_Mono8 == enGvspPixelType or PixelType_Gvsp_Mono10 == enGvspPixelType \
            or PixelType_Gvsp_Mono10_Packed == enGvspPixelType or PixelType_Gvsp_Mono12 == enGvspPixelType \
            or PixelType_Gvsp_Mono12_Packed == enGvspPixelType:
        return True
    else:
        return False


# 是否是彩色图像
def Is_color_data(enGvspPixelType):
    if PixelType_Gvsp_BayerGR8 == enGvspPixelType or PixelType_Gvsp_BayerRG8 == enGvspPixelType \
            or PixelType_Gvsp_BayerGB8 == enGvspPixelType or PixelType_Gvsp_BayerBG8 == enGvspPixelType \
            or PixelType_Gvsp_BayerGR10 == enGvspPixelType or PixelType_Gvsp_BayerRG10 == enGvspPixelType \
            or PixelType_Gvsp_BayerGB10 == enGvspPixelType or PixelType_Gvsp_BayerBG10 == enGvspPixelType \
            or PixelType_Gvsp_BayerGR12 == enGvspPixelType or PixelType_Gvsp_BayerRG12 == enGvspPixelType \
            or PixelType_Gvsp_BayerGB12 == enGvspPixelType or PixelType_Gvsp_BayerBG12 == enGvspPixelType \
            or PixelType_Gvsp_BayerGR10_Packed == enGvspPixelType or PixelType_Gvsp_BayerRG10_Packed == enGvspPixelType \
            or PixelType_Gvsp_BayerGB10_Packed == enGvspPixelType or PixelType_Gvsp_BayerBG10_Packed == enGvspPixelType \
            or PixelType_Gvsp_BayerGR12_Packed == enGvspPixelType or PixelType_Gvsp_BayerRG12_Packed == enGvspPixelType \
            or PixelType_Gvsp_BayerGB12_Packed == enGvspPixelType or PixelType_Gvsp_BayerBG12_Packed == enGvspPixelType \
            or PixelType_Gvsp_YUV422_Packed == enGvspPixelType or PixelType_Gvsp_YUV422_YUYV_Packed == enGvspPixelType:
        return True
    else:
        return False


# Mono图像转为python数组
def Mono_numpy(data, nWidth, nHeight):
    data_ = np.frombuffer(data, count=int(nWidth * nHeight), dtype=np.uint8, offset=0)
    data_mono_arr = data_.reshape(nHeight, nWidth)
    numArray = np.zeros([nHeight, nWidth, 1], "uint8")
    numArray[:, :, 0] = data_mono_arr
    return numArray
    # 1通道，维度：nWidth,nHeight,1


# 彩色图像转为python数组
def Color_numpy(data, nWidth, nHeight):
    data_ = np.frombuffer(data, count=int(nWidth * nHeight * 3), dtype=np.uint8, offset=0)
    data_r = data_[0:nWidth * nHeight * 3:3]
    data_g = data_[1:nWidth * nHeight * 3:3]
    data_b = data_[2:nWidth * nHeight * 3:3]
    # 最后一个3为步长

    data_r_arr = data_r.reshape(nHeight, nWidth)
    data_g_arr = data_g.reshape(nHeight, nWidth)
    data_b_arr = data_b.reshape(nHeight, nWidth)
    numArray = np.zeros([nHeight, nWidth, 3], "uint8")

    numArray[:, :, 0] = data_r_arr
    numArray[:, :, 1] = data_g_arr
    numArray[:, :, 2] = data_b_arr
    return numArray
    # 3通道，nWidth,nHeight,3


# 相机操作类
class CameraOperation:

    def __init__(self, obj_cam, st_device_list, n_connect_num=0, b_open_device=False, b_start_grabbing=False,
                 h_thread_handle=None,
                 b_thread_closed=False, st_frame_info=None, b_exit=False, b_save_bmp=False, b_save_jpg=False,
                 buf_save_image=None,
                 n_save_image_size=0, n_win_gui_id=0, frame_rate=0, exposure_time=0, gain=0, image_width=0,
                 image_height=0, resulting_frame_rate=0, b_start_recording=False):

        self.obj_cam = obj_cam
        self.st_device_list = st_device_list
        self.n_connect_num = n_connect_num
        self.b_open_device = b_open_device
        self.b_start_grabbing = b_start_grabbing
        self.b_thread_closed = b_thread_closed
        self.st_frame_info = st_frame_info
        self.b_exit = b_exit
        self.b_save_bmp = b_save_bmp
        self.b_save_jpg = b_save_jpg
        self.buf_grab_image = None
        self.buf_grab_image_size = 0
        self.buf_save_image = buf_save_image
        self.n_save_image_size = n_save_image_size
        self.h_thread_handle = h_thread_handle
        self.frame_rate = frame_rate
        self.exposure_time = exposure_time
        self.gain = gain
        self.buf_lock = threading.Lock()  # 取图和存图的buffer锁
        self.image_width = image_width
        self.image_height = image_height
        self.b_start_recroding = b_start_recording
        self.resulting_frame_rate = resulting_frame_rate

    # 打开相机
    def Open_device(self):
        if not self.b_open_device:
            if self.n_connect_num < 0:
                return MV_E_CALLORDER

            # ch:选择设备并创建句柄 | en:Select device and create handle
            nConnectionNum = int(self.n_connect_num)
            stDeviceList = cast(self.st_device_list.pDeviceInfo[int(nConnectionNum)],
                                POINTER(MV_CC_DEVICE_INFO)).contents
            self.obj_cam = MvCamera()
            ret = self.obj_cam.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                self.obj_cam.MV_CC_DestroyHandle()
                return ret

            ret = self.obj_cam.MV_CC_OpenDevice()
            if ret != 0:
                return ret
            # print("open device successfully!")
            self.b_open_device = True
            self.b_thread_closed = False

            # ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
            if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
                nPacketSize = self.obj_cam.MV_CC_GetOptimalPacketSize()
                if int(nPacketSize) > 0:
                    ret = self.obj_cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)
                    if ret != 0:
                        print("warning: set packet size fail! ret[0x%x]" % ret)
                else:
                    print("warning: set packet size fail! ret[0x%x]" % nPacketSize)

            stBool = c_bool(False)
            ret = self.obj_cam.MV_CC_GetBoolValue("AcquisitionFrameRateEnable", stBool)
            if ret != 0:
                print("get acquisition frame rate enable fail! ret[0x%x]" % ret)

            # ch:设置触发模式为off | en:Set trigger mode as off
            ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
            if ret != 0:
                print("set trigger mode fail! ret[0x%x]" % ret)
            return MV_OK

    # 开始取图
    def Start_grabbing(self, win_handle, is_saving, save_path, is_compression):
        if self.st_frame_info is None:
            self.st_frame_info = MV_FRAME_OUT()
            memset(byref(self.st_frame_info), 0, sizeof(self.st_frame_info))
        if not self.b_start_grabbing and self.b_open_device:
            self.b_exit = False
            ret = self.obj_cam.MV_CC_StartGrabbing()
            if ret != 0:
                return ret
            self.b_start_grabbing = True
            print("start grabbing successfully!")
            try:
                thread_id = random.randint(1, 10000)
                if is_saving:
                    if is_compression:
                        self.h_thread_handle = threading.Thread(target=CameraOperation.Work_thread4, args=(self, win_handle, save_path))
                    else:
                        self.h_thread_handle = threading.Thread(target=CameraOperation.Work_thread3,args=(self, win_handle, save_path))
                else:
                    if is_compression:
                        self.h_thread_handle = threading.Thread(target=CameraOperation.Work_thread2, args=(self, win_handle))
                    else:
                        self.h_thread_handle = threading.Thread(target=CameraOperation.Work_thread1,args=(self, win_handle))
                self.h_thread_handle.start()
                self.b_thread_closed = True
            finally:
                pass
            return MV_OK

        return MV_E_CALLORDER

    # 停止取图
    def Stop_grabbing(self):
        if self.b_start_grabbing and self.b_open_device:
            # 退出线程
            if self.b_thread_closed:
                Stop_thread(self.h_thread_handle)
                self.b_thread_closed = False
            ret = self.obj_cam.MV_CC_StopGrabbing()
            if ret != 0:
                return ret
            print("stop grabbing successfully!")
            self.b_start_grabbing = False
            self.b_exit = True
            return MV_OK
        else:
            return MV_E_CALLORDER

    # 关闭相机
    def Close_device(self):
        if self.b_open_device:
            # 退出线程
            if self.b_thread_closed:
                Stop_thread(self.h_thread_handle)
                self.b_thread_closed = False
            ret = self.obj_cam.MV_CC_CloseDevice()
            if ret != 0:
                return ret

        # ch:销毁句柄 | Destroy handle
        self.obj_cam.MV_CC_DestroyHandle()
        self.b_open_device = False
        self.b_start_grabbing = False
        self.b_exit = True
        # print("close device successfully!")

        return MV_OK

    # 设置触发模式
    def Set_trigger_mode(self, is_trigger_mode, is_soft_trigger):
        if not self.b_open_device:
            return MV_E_CALLORDER

        if not is_trigger_mode:
            ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", 0)
            if ret != 0:
                return ret
        else:
            ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", 1)
            if ret != 0:
                return ret
            if is_soft_trigger:
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerSource", 7)
            else:
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerSource", 0)#Line0触发
            if ret != 0:
                return ret

        return MV_OK

    # 软触发一次
    def Trigger_once(self):
        if self.b_open_device:
            return self.obj_cam.MV_CC_SetCommandValue("TriggerSoftware")

    # 获取参数
    def Get_parameter(self):
        if self.b_open_device:
            stFloatParam_FrameRate = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_FrameRate), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_exposureTime = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_exposureTime), 0, sizeof(MVCC_FLOATVALUE))

            stFloatParam_gain = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_gain), 0, sizeof(MVCC_FLOATVALUE))

            stIntParam_ImageWidth = MVCC_INTVALUE()
            memset(byref(stIntParam_ImageWidth), 0, sizeof(MVCC_INTVALUE))
            stIntParam_ImageHeight = MVCC_INTVALUE()
            memset(byref(stIntParam_ImageHeight), 0, sizeof(MVCC_INTVALUE))

            stFloatParam_ResultingFrameRate = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_ResultingFrameRate), 0, sizeof(MVCC_FLOATVALUE))

            ret = self.obj_cam.MV_CC_GetFloatValue("AcquisitionFrameRate", stFloatParam_FrameRate)
            if ret != 0:
                return ret
            self.frame_rate = stFloatParam_FrameRate.fCurValue

            ret = self.obj_cam.MV_CC_GetFloatValue("ExposureTime", stFloatParam_exposureTime)
            if ret != 0:
                return ret
            self.exposure_time = stFloatParam_exposureTime.fCurValue

            ret = self.obj_cam.MV_CC_GetFloatValue("Gain", stFloatParam_gain)
            if ret != 0:
                return ret
            self.gain = stFloatParam_gain.fCurValue

            ret = self.obj_cam.MV_CC_GetIntValueEx("Width", stIntParam_ImageWidth)
            if ret != 0:
                return ret
            self.image_width = stIntParam_ImageWidth.nCurValue
            # print("max width=",stIntParam_ImageWidth.nMax,"   min width=",stIntParam_ImageWidth.nMin)

            ret = self.obj_cam.MV_CC_GetIntValueEx("Height", stIntParam_ImageHeight)
            if ret != 0:
                return ret
            self.image_height = stIntParam_ImageHeight.nCurValue
            # print("max height=", stIntParam_ImageWidth.nMax, "   min height=", stIntParam_ImageWidth.nMin)

            ret = self.obj_cam.MV_CC_GetFloatValue("ResultingFrameRate", stFloatParam_ResultingFrameRate)
            if ret != 0:
                return ret
            self.resulting_frame_rate = stFloatParam_ResultingFrameRate.fCurValue
            return MV_OK

    # 设置参数
    def Set_parameter(self, frame_rate, exposure_time, image_width, image_height):
        if self.b_open_device:
            if frame_rate != '':
                ret = self.obj_cam.MV_CC_SetFloatValue("AcquisitionFrameRate", float(frame_rate))
                if ret != 0:
                    print('show error', 'set acquistion frame rate fail! ret = ' + To_hex_str(ret))
                    return ret
            if exposure_time != '':
                ret = self.obj_cam.MV_CC_SetFloatValue("ExposureTime", float(exposure_time))
                if ret != 0:
                    print('show error', 'set exposure time fail! ret = ' + To_hex_str(ret))
                    return ret
            if image_width != '':
                ret = self.obj_cam.MV_CC_SetIntValueEx("Width", int(image_width))
                if ret != 0:
                    print('show error', 'set image width fail! ret = ' + To_hex_str(ret))
                    return ret
            if image_height != '':
                ret = self.obj_cam.MV_CC_SetIntValueEx("Height", int(image_height))
                if ret != 0:
                    print('show error', 'set image width fail! ret = ' + To_hex_str(ret))
                    return ret
            print('show info', 'set parameter success!')
            return MV_OK
    '''        
    # 设置参数
    def Set_parameter(self, frameRate, exposureTime, gain):
        if '' == frameRate or '' == exposureTime or '' == gain:
            print('show info', 'please type in the text box !')
            return MV_E_PARAMETER
        if self.b_open_device:
            ret = self.obj_cam.MV_CC_SetFloatValue("ExposureTime", float(exposureTime))
            if ret != 0:
                print('show error', 'set exposure time fail! ret = ' + To_hex_str(ret))
                return ret

            ret = self.obj_cam.MV_CC_SetFloatValue("Gain", float(gain))
            if ret != 0:
                print('show error', 'set gain fail! ret = ' + To_hex_str(ret))
                return ret

            ret = self.obj_cam.MV_CC_SetFloatValue("AcquisitionFrameRate", float(frameRate))
            if ret != 0:
                print('show error', 'set acquistion frame rate fail! ret = ' + To_hex_str(ret))
                return ret

            print('show info', 'set parameter success!')

            return MV_OK
    '''
    # 取图线程函数
    def Work_thread(self, win_hand):
        # stOutFrame = MV_FRAME_OUT()
        # MV_FRAME_OUT_INFO_EX参考CameraParams_header.py Line:269 定义了图像宽高，帧号，帧长度，像素格式等信息。
        stFrameInfo = MV_FRAME_OUT_INFO_EX()
        img_buff = None
        numArray = None

        # MVCC_INTVALUE_EX参考CameraParams_header.py Line:644，定义当前值，最大值，最小值，步长等信息
        # 通过MV_CC_GetIntValue,获取stPayLoadSize，获取需要的缓冲区大小
        stPayloadSize = MVCC_INTVALUE_EX()
        ret_temp = self.obj_cam.MV_CC_GetIntValueEx("PayloadSize", stPayloadSize)
        if ret_temp != MV_OK:
            return
        # 需要的缓冲区大小
        NeedBufSize = int(stPayloadSize.nCurValue)

        while True:
            if self.buf_grab_image_size < NeedBufSize:
                # self.buf_grab_image缓冲区，初始化为None，buf_grab_image_size缓冲区大小，初始化为0
                self.buf_grab_image = (c_ubyte * NeedBufSize)()
                self.buf_grab_image_size = NeedBufSize

            ret = self.obj_cam.MV_CC_GetOneFrameTimeout(self.buf_grab_image, self.buf_grab_image_size, stFrameInfo)

            print("PayloadSize:", NeedBufSize, "   stFrameInfo.nFrameLen:", stFrameInfo.nFrameLen)
            '''
            stPayloadSize的大小等于stFrameInfo.nFrameLen，等于分辨率2448*2048=5013504
            '''
            print("stFrameInfo.enPixelType", stFrameInfo.enPixelType)
            # ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 1000)
            if 0 == ret:
                # 拷贝图像和图像信息
                if self.buf_save_image is None:
                    self.buf_save_image = (c_ubyte * stFrameInfo.nFrameLen)()
                self.st_frame_info = stFrameInfo

                # 获取缓存锁
                # self.buf_lock.acquire()
                cdll.msvcrt.memcpy(byref(self.buf_save_image), self.buf_grab_image, self.st_frame_info.nFrameLen)
                # self.buf_lock.release()
                '''
                print("get one frame: Width[%d], Height[%d], nFrameNum[%d]"
                      % (self.st_frame_info.nWidth, self.st_frame_info.nHeight, self.st_frame_info.nFrameNum))
                '''
                # 释放缓存
                # self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)
            else:
                print("no data, ret = " + To_hex_str(ret))
                continue


            #保存图像
            # self.Save_jpg()

            # 使用Display接口显示图像
            stDisplayParam = MV_DISPLAY_FRAME_INFO()
            memset(byref(stDisplayParam), 0, sizeof(stDisplayParam))
            stDisplayParam.hWnd = int(win_hand)
            stDisplayParam.nWidth = self.st_frame_info.nWidth
            stDisplayParam.nHeight = self.st_frame_info.nHeight
            stDisplayParam.enPixelType = self.st_frame_info.enPixelType
            stDisplayParam.pData = self.buf_save_image
            stDisplayParam.nDataLen = self.st_frame_info.nFrameLen
            self.obj_cam.MV_CC_DisplayOneFrame(stDisplayParam)

            # 是否退出
            if self.b_exit:
                if img_buff is not None:
                    del img_buff
                if self.buf_save_image is not None:
                    del self.buf_save_image
                break


    # 取图线程函数:采用mvcc_get_imagebuffer
    def Work_thread1(self, win_hand):
        stOutFrame = MV_FRAME_OUT()
        memset(byref((stOutFrame)), 0, sizeof(stOutFrame))

        stPayloadSize = MVCC_INTVALUE_EX()
        memset((byref(stPayloadSize)), 0, sizeof(stPayloadSize))
        ret_temp = self.obj_cam.MV_CC_GetIntValueEx("PayloadSize", stPayloadSize)
        if ret_temp != MV_OK:
            return
        NeedBufSize = int(stPayloadSize.nCurValue)  # 需要的缓冲区大小
        flag = False
        while True:
            ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 5000)
            if 0 == ret:
                # 拷贝图像和图像信息
                if self.buf_save_image is None:
                    self.buf_save_image = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                if not flag:
                    self.st_frame_info.nWidth = stOutFrame.stFrameInfo.nWidth
                    self.st_frame_info.nHeight = stOutFrame.stFrameInfo.nHeight
                    self.st_frame_info.nFrameLen = stOutFrame.stFrameInfo.nFrameLen
                    self.st_frame_info.enPixelType = stOutFrame.stFrameInfo.enPixelType
                    flag = True
                self.st_frame_info.nFrameNum = stOutFrame.stFrameInfo.nFrameNum

                cdll.msvcrt.memcpy(byref(self.buf_save_image), stOutFrame.pBufAddr, self.st_frame_info.nFrameLen)

                '''
                print("get one frame: Width[%d], Height[%d], nFrameNum[%d]"
                      % (self.st_frame_info.nWidth, self.st_frame_info.nHeight, self.st_frame_info.nFrameNum))
                
                print("*********************************")
                print("PayloadSize:", NeedBufSize, "   stFrameInfo.nFrameLen:", stOutFrame.stFrameInfo.nFrameLen ,"stFrameInfo.enPixelType", stOutFrame.stFrameInfo.enPixelType)
                print("*******************************")
                '''
                # 释放缓存
                self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)
            else:
                print("no data, ret = " + To_hex_str(ret))
                continue


            #保存图像
            # self.Save_jpg()

            # 使用Display接口显示图像
            stDisplayParam = MV_DISPLAY_FRAME_INFO()
            memset(byref(stDisplayParam), 0, sizeof(stDisplayParam))
            stDisplayParam.hWnd = int(win_hand)
            stDisplayParam.nWidth = self.st_frame_info.nWidth
            stDisplayParam.nHeight = self.st_frame_info.nHeight
            stDisplayParam.enPixelType = self.st_frame_info.enPixelType
            stDisplayParam.pData = self.buf_save_image
            stDisplayParam.nDataLen = self.st_frame_info.nFrameLen
            self.obj_cam.MV_CC_DisplayOneFrame(stDisplayParam)

            # 是否退出
            if self.b_exit:
                if self.buf_save_image is not None:
                    del self.buf_save_image
                    del self.st_frame_info
                break

    # 取图线程函数:采用mvcc_get_imagebuffer,加入无损压缩后的解码
    def Work_thread2(self, win_hand):
        stOutFrame = MV_FRAME_OUT()
        memset(byref((stOutFrame)), 0, sizeof(stOutFrame))

        stDecodeParam = MV_CC_HB_DECODE_PARAM()
        memset(byref(stDecodeParam), 0, sizeof((stDecodeParam)))


        stPayloadSize = MVCC_INTVALUE_EX()
        memset((byref(stPayloadSize)), 0, sizeof(stPayloadSize))
        ret_temp = self.obj_cam.MV_CC_GetIntValueEx("PayloadSize", stPayloadSize)
        if ret_temp != MV_OK:
            return
        NeedBufSize = int(stPayloadSize.nCurValue)  # 需要的缓冲区大小
        pDstBuf =None
        flag = False
        while True:
            ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 1000)
            if 0 == ret:
                stDecodeParam.pSrcBuf = stOutFrame.pBufAddr
                stDecodeParam.nSrcLen = stOutFrame.stFrameInfo.nFrameLen
                if pDstBuf is None:
                    pDstBuf = (c_ubyte * NeedBufSize)()
                stDecodeParam.pDstBuf = pDstBuf
                stDecodeParam.nDstBufSize = NeedBufSize

                ret = self.obj_cam.MV_CC_HB_Decode(stDecodeParam)
                '''
                print("*********************************")
                print("PayloadSize:", NeedBufSize, "   stFrameInfo.nFrameLen:", stOutFrame.stFrameInfo.nFrameLen,
                      "stFrameInfo.enPixelType", stOutFrame.stFrameInfo.enPixelType)
                print("nSrcLen:",stDecodeParam.nSrcLen,"nDstBufSize:",stDecodeParam.nDstBufSize,"nDstBufLen",stDecodeParam.nDstBufLen)
                print("enDstPixelType",stDecodeParam.enDstPixelType)
                print("nWidth",stDecodeParam.nWidth,"nHeight",stDecodeParam.nHeight)
                print("*******************************")
                '''
                if ret != MV_OK:
                    print("strError:数据解压缩失败  错误码：",To_hex_str(ret),"错误类型：参数错误")
                # 拷贝图像和图像信息
                if self.buf_save_image is None:
                    self.buf_save_image = (c_ubyte * NeedBufSize)()
                # 采用无损压缩，不能直接，self.st_frame_info = stOutFrame.stFrameInfo，否则调用sava_jpg的时候会出现参数错误
                if not flag:
                    self.st_frame_info = stOutFrame.stFrameInfo
                    self.st_frame_info.nFrameLen = stDecodeParam.nDstBufLen
                    self.st_frame_info.enPixelType = stDecodeParam.enDstPixelType
                    flag = True
                self.st_frame_info.nFrameNum = stOutFrame.stFrameInfo.nFrameNum

                # self.buf_lock.acquire()
                # !!!注意，此处第三个参数，不能写stDecodeParam.nDstBufSize，需要些stDecodeParam.nDstBufLen
                cdll.msvcrt.memcpy(byref(self.buf_save_image), stDecodeParam.pDstBuf, stDecodeParam.nDstBufLen)
                # self.buf_lock.release()
                '''
                print("get one frame: Width[%d], Height[%d], nFrameNum[%d]"
                      % (self.st_frame_info.nWidth, self.st_frame_info.nHeight, self.st_frame_info.nFrameNum))
                '''
                # 释放缓存
                self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)
            else:
                print("no data, ret = " + To_hex_str(ret))
                continue


            #保存图像
            # self.Save_jpg()

            # 使用Display接口显示图像
            stDisplayParam = MV_DISPLAY_FRAME_INFO()
            memset(byref(stDisplayParam), 0, sizeof(stDisplayParam))
            stDisplayParam.hWnd = int(win_hand)
            stDisplayParam.nWidth = self.st_frame_info.nWidth
            stDisplayParam.nHeight = self.st_frame_info.nHeight
            stDisplayParam.enPixelType = stDecodeParam.enDstPixelType
            stDisplayParam.pData = self.buf_save_image
            stDisplayParam.nDataLen = stDecodeParam.nDstBufLen
            ret = self.obj_cam.MV_CC_DisplayOneFrame(stDisplayParam)
            if ret != MV_OK:
                print("display failed:",To_hex_str(ret))

            # 是否退出
            if self.b_exit:
                if self.buf_save_image is not None:
                    del self.buf_save_image
                    del self.st_frame_info
                break


# 取图并保存线程函数，不采用无损压缩
    def Work_thread3(self, win_hand, save_path):
        stOutFrame = MV_FRAME_OUT()
        memset(byref((stOutFrame)), 0, sizeof(stOutFrame))

        stPayloadSize = MVCC_INTVALUE_EX()
        memset((byref(stPayloadSize)), 0, sizeof(stPayloadSize))
        ret_temp = self.obj_cam.MV_CC_GetIntValueEx("PayloadSize", stPayloadSize)
        if ret_temp != MV_OK:
            return
        NeedBufSize = int(stPayloadSize.nCurValue)  # 需要的缓冲区大小
        flag = False
        while True:
            ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 1000)
            if 0 == ret:
                # 拷贝图像和图像信息
                if self.buf_save_image is None:
                    self.buf_save_image = (c_ubyte * stOutFrame.stFrameInfo.nFrameLen)()
                # self.st_frame_info = stOutFrame.stFrameInfo
                if not flag:
                    self.st_frame_info.nWidth = stOutFrame.stFrameInfo.nWidth
                    self.st_frame_info.nHeight = stOutFrame.stFrameInfo.nHeight
                    self.st_frame_info.nFrameLen = stOutFrame.stFrameInfo.nFrameLen
                    self.st_frame_info.enPixelType = stOutFrame.stFrameInfo.enPixelType
                    flag = True
                self.st_frame_info.nFrameNum = stOutFrame.stFrameInfo.nFrameNum

                cdll.msvcrt.memcpy(byref(self.buf_save_image), stOutFrame.pBufAddr, self.st_frame_info.nFrameLen)

                '''
                print("get one frame: Width[%d], Height[%d], nFrameNum[%d]"
                      % (self.st_frame_info.nWidth, self.st_frame_info.nHeight, self.st_frame_info.nFrameNum))
                
                print("*********************************")
                print("PayloadSize:", NeedBufSize, "   stFrameInfo.nFrameLen:", stOutFrame.stFrameInfo.nFrameLen ,"stFrameInfo.enPixelType", stOutFrame.stFrameInfo.enPixelType)
                print("*******************************")
                '''
                # 释放缓存
                self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)
            else:
                print("no data, ret = " + To_hex_str(ret))
                continue


            #保存图像
            self.Save_jpg(save_path)

            # 使用Display接口显示图像
            stDisplayParam = MV_DISPLAY_FRAME_INFO()
            memset(byref(stDisplayParam), 0, sizeof(stDisplayParam))
            stDisplayParam.hWnd = int(win_hand)
            stDisplayParam.nWidth = self.st_frame_info.nWidth
            stDisplayParam.nHeight = self.st_frame_info.nHeight
            stDisplayParam.enPixelType = self.st_frame_info.enPixelType
            stDisplayParam.pData = self.buf_save_image
            stDisplayParam.nDataLen = self.st_frame_info.nFrameLen
            self.obj_cam.MV_CC_DisplayOneFrame(stDisplayParam)

            # 是否退出
            if self.b_exit:
                if self.buf_save_image is not None:
                    del self.buf_save_image
                    del self.st_frame_info
                break


    # 取图并保存线程函数,采用无损压缩
    def Work_thread4(self, win_hand, save_path):
        stOutFrame = MV_FRAME_OUT()
        memset(byref((stOutFrame)), 0, sizeof(stOutFrame))

        stDecodeParam = MV_CC_HB_DECODE_PARAM()
        memset(byref(stDecodeParam), 0, sizeof((stDecodeParam)))

        stPayloadSize = MVCC_INTVALUE_EX()
        memset((byref(stPayloadSize)), 0, sizeof(stPayloadSize))
        ret_temp = self.obj_cam.MV_CC_GetIntValueEx("PayloadSize", stPayloadSize)
        if ret_temp != MV_OK:
            return
        NeedBufSize = int(stPayloadSize.nCurValue)  # 需要的缓冲区大小
        pDstBuf = None
        flag = False
        while True:
            ret = self.obj_cam.MV_CC_GetImageBuffer(stOutFrame, 1000)
            if 0 == ret:
                stDecodeParam.pSrcBuf = stOutFrame.pBufAddr
                stDecodeParam.nSrcLen = stOutFrame.stFrameInfo.nFrameLen
                if pDstBuf is None:
                    pDstBuf = (c_ubyte * NeedBufSize)()
                stDecodeParam.pDstBuf = pDstBuf
                stDecodeParam.nDstBufSize = NeedBufSize

                ret = self.obj_cam.MV_CC_HB_Decode(stDecodeParam)
                if ret != MV_OK:
                    print("strError:数据解压缩失败  错误码：", To_hex_str(ret), "错误类型：参数错误")
                # 拷贝图像和图像信息
                if self.buf_save_image is None:
                    self.buf_save_image = (c_ubyte * NeedBufSize)()
                # 采用无损压缩，不能直接，self.st_frame_info = stOutFrame.stFrameInfo，否则调用sava_jpg的时候会出现参数错误
                if not flag:
                    self.st_frame_info.nWidth = stOutFrame.stFrameInfo.nWidth
                    self.st_frame_info.nHeight = stOutFrame.stFrameInfo.nHeight
                    self.st_frame_info.nFrameLen = stDecodeParam.nDstBufLen
                    self.st_frame_info.enPixelType = stDecodeParam.enDstPixelType
                    flag = True
                self.st_frame_info.nFrameNum = stOutFrame.stFrameInfo.nFrameNum
                # self.buf_lock.acquire()
                # !!!注意，此处第三个参数，不能写stDecodeParam.nDstBufSize，需要些stDecodeParam.nDstBufLen
                cdll.msvcrt.memcpy(byref(self.buf_save_image), stDecodeParam.pDstBuf, stDecodeParam.nDstBufLen)
                # self.buf_lock.release()

                # 释放缓存
                self.obj_cam.MV_CC_FreeImageBuffer(stOutFrame)
            else:
                print("no data, ret = " + To_hex_str(ret))
                continue

            # 保存图像
            self.Save_jpg(save_path)
            '''
            # 使用Display接口显示图像
            stDisplayParam = MV_DISPLAY_FRAME_INFO()
            memset(byref(stDisplayParam), 0, sizeof(stDisplayParam))
            stDisplayParam.hWnd = int(win_hand)
            stDisplayParam.nWidth = self.st_frame_info.nWidth
            stDisplayParam.nHeight = self.st_frame_info.nHeight
            stDisplayParam.enPixelType = stDecodeParam.enDstPixelType
            stDisplayParam.pData = self.buf_save_image
            stDisplayParam.nDataLen = stDecodeParam.nDstBufLen
            ret = self.obj_cam.MV_CC_DisplayOneFrame(stDisplayParam)
            if ret != MV_OK:
                print("display failed:", To_hex_str(ret))
            '''


            # 是否退出
            if self.b_exit:
                if self.buf_save_image is not None:
                    del self.buf_save_image
                    del self.st_frame_info
                break

    # 存jpg图像
    def Save_jpg(self, save_path):
        # print(save_path)
        if not os.path.lexists(save_path):
            os.mkdir(save_path)
        if self.buf_save_image is None:
            return
        file_path = save_path + "\\" + str(self.st_frame_info.nFrameNum) + ".jpg"

        stSaveParam = MV_SAVE_IMG_TO_FILE_PARAM()
        stSaveParam.enPixelType = self.st_frame_info.enPixelType  # ch:相机对应的像素格式 | en:Camera pixel type
        stSaveParam.nWidth = self.st_frame_info.nWidth  # ch:相机对应的宽 | en:Width
        stSaveParam.nHeight = self.st_frame_info.nHeight  # ch:相机对应的高 | en:Height
        stSaveParam.nDataLen = self.st_frame_info.nFrameLen

        # 获取缓存锁
        self.buf_lock.acquire()
        stSaveParam.pData = cast(self.buf_save_image, POINTER(c_ubyte))
        self.buf_lock.release()

        stSaveParam.enImageType = MV_Image_Jpeg  # ch:需要保存的图像类型 | en:Image format to save
        stSaveParam.nQuality = 80
        stSaveParam.pImagePath = file_path.encode('ascii')
        stSaveParam.iMethodValue = 2
        ret = self.obj_cam.MV_CC_SaveImageToFile(stSaveParam)

        return ret

    # 存BMP图像
    def Save_Bmp(self):

        if 0 == self.buf_save_image:
            return

        # 获取缓存锁
        self.buf_lock.acquire()

        file_path = str(self.st_frame_info.nFrameNum) + ".bmp"

        stSaveParam = MV_SAVE_IMG_TO_FILE_PARAM()
        stSaveParam.enPixelType = self.st_frame_info.enPixelType  # ch:相机对应的像素格式 | en:Camera pixel type
        stSaveParam.nWidth = self.st_frame_info.nWidth  # ch:相机对应的宽 | en:Width
        stSaveParam.nHeight = self.st_frame_info.nHeight  # ch:相机对应的高 | en:Height
        stSaveParam.nDataLen = self.st_frame_info.nFrameLen
        stSaveParam.pData = cast(self.buf_save_image, POINTER(c_ubyte))
        stSaveParam.enImageType = MV_Image_Bmp  # ch:需要保存的图像类型 | en:Image format to save
        stSaveParam.nQuality = 8
        stSaveParam.pImagePath = file_path.encode('ascii')
        stSaveParam.iMethodValue = 2
        ret = self.obj_cam.MV_CC_SaveImageToFile(stSaveParam)

        self.buf_lock.release()
        return ret

    # 开启无损压缩
    def Compression_On(self):
        ret = self.obj_cam.MV_CC_SetEnumValue("ImageCompressionMode", 2) #0-off，2-HB
        if ret != 0:
            return ret
        else:
            ret = self.obj_cam.MV_CC_SetEnumValue("HighBandwidthMode", 1) #1-Brust,0-Compression
        return ret

    # 关闭无损压缩
    def Compression_Off(self):
        ret = self.obj_cam.MV_CC_SetEnumValue("ImageCompressionMode", 0)  # 0-off，2-HB
        return ret

    def SetFreamRate_Enable(self, enable):
        ret = self.obj_cam.MV_CC_SetBoolValue("AcquisitionFrameRateEnable",enable)
        return ret

    def Acquisition_info(self):
        acq_info = MV_NETTRANS_INFO()
        memset(byref(acq_info), 0, sizeof(acq_info))
        ret = self.obj_cam.MV_GIGE_GetNetTransInfo(acq_info)
        return ret, acq_info.nThrowFrameCount, acq_info.nNetRecvFrameCount
