from PyQt5.QtWidgets import *
from PyQt5.QtCore import QTime, QTimer
from PyQt5.QtGui import QIcon
from CamOperation_class import CameraOperation
from MvCameraControl_class import *
from MvErrorDefine_const import *
from CameraParams_header import *
from MvCameraUi import Ui_MainWindow
from CommonHelper import CommonHelper
import os


# 将返回的错误码转换为十六进制显示
def ToHexStr(num):
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

if __name__ == "__main__":
    global deviceList
    deviceList = 0
    global cam
    cam = MvCamera()
    global obj_cam_operations
    obj_cam_operations = []
    global isEnmu
    isEnmu = False
    global isOpen
    isOpen = False
    global isGrabbing
    isGrabbing = False
    global isCalibMode  # 是否是标定模式（获取原始图像）
    isCalibMode = True
    global isContinueMode
    isContinueMode = False
    global devList  # 设备信息列表
    devList = []
    global bTriggerOnce # 是否触发一次，防止未触发就保存图片
    bTriggerOnce = False
    global isRecording
    isRecording = False
    global savePath
    savePath = os.getcwd()
    savePath = savePath.replace("\\","/")
    global counter # 计时器,负责展示录制时间
    counter = QTime()
    global timer # 定时器
    timer = QTimer()
    global counter_info#负责展示丢帧信息
    counter_info = QTime()
    global timer_info
    timer_info = QTimer()
    global isSoftTrigger
    isSoftTrigger =False
    global comSel
    comSel = 0
    global maxImgWeight
    maxImgWeight = 2448
    global maxImgHeight
    maxImgHeight = 2048
    global isCompression
    isCompression = False
    # 要展示的设备信息
    global devInfo
    devInfo={
        "ip": [],
        "MAC": [],
        "ModeName": "MV-CS050-10GC-PRO",
        "VendorName": "Hikrobot"
    }
    global recvFrameCount
    recvFrameCount = 0

    # 槽函数
    # 枚举相机
    def enum_devices():
        global deviceList
        global devList
        global isEnmu
        global devInfo
        if isEnmu:
            return
        ui.btnEnum.setIcon(QIcon('./icon/search.png'))
        deviceList = MV_CC_DEVICE_INFO_LIST()
        ret = MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE, deviceList)
        if ret != 0:
            strError = "Enum devices fail! ret = :" + ToHexStr(ret)
            QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
            return ret

        if deviceList.nDeviceNum == 0:
            QMessageBox.warning(mainWindow, "Info", "Find no device", QMessageBox.Ok)
            return ret
        print("Find %d devices!" % deviceList.nDeviceNum)

        devList = []
        # 设备名列表
        for i in range(0, deviceList.nDeviceNum):
            mvcc_dev_info = cast(deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
                print("\ngige device: [%d]" % i)
                chUserDefinedName = ""
                for per in mvcc_dev_info.SpecialInfo.stGigEInfo.chUserDefinedName:
                    if 0 == per:
                        break
                    chUserDefinedName = chUserDefinedName + chr(per)
                print("device user define name: %s" % chUserDefinedName)

                chModelName = ""
                for per in mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName:
                    if 0 == per:
                        break
                    chModelName = chModelName + chr(per)

                print("device model name: %s" % chModelName)
                devInfo['ModeName'] = chModelName
                # ip
                nip1 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
                nip2 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
                nip3 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
                nip4 = (mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
                print("current ip: %d.%d.%d.%d\n" % (nip1, nip2, nip3, nip4))
                devInfo["ip"].append("%d.%d.%d.%d" % (nip1, nip2, nip3, nip4))

                # MAC
                nmac1 = (mvcc_dev_info.nMacAddrHigh & 0x0000ff00) >> 8
                nmac2 = (mvcc_dev_info.nMacAddrHigh & 0x000000ff)
                nmac3 = (mvcc_dev_info.nMacAddrLow  & 0xff000000) >> 24
                nmac4 = (mvcc_dev_info.nMacAddrLow  & 0x00ff0000) >> 16
                nmac5 = (mvcc_dev_info.nMacAddrLow  & 0x0000ff00) >> 8
                nmac6 = (mvcc_dev_info.nMacAddrLow & 0x000000ff)
                devInfo["MAC"].append("%x:%x:%x:%x:%x:%x" % (nmac1, nmac2, nmac3, nmac4, nmac5, nmac6))
                #print("MAC:", ToHexStr(mvcc_dev_info.nMacAddrHigh), ToHexStr(mvcc_dev_info.nMacAddrLow))
                devList.append(
                    "[" + str(i) + "]GigE: " + chUserDefinedName + " " + chModelName + "(" + str(nip1) + "." + str(
                        nip2) + "." + str(nip3) + "." + str(nip4) + ")")
            elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
                print("\nu3v device: [%d]" % i)
                chUserDefinedName = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chUserDefinedName:
                    if per == 0:
                        break
                    chUserDefinedName = chUserDefinedName + chr(per)
                print("device user define name: %s" % chUserDefinedName)

                chModelName = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName:
                    if 0 == per:
                        break
                    chModelName = chModelName + chr(per)
                print("device model name: %s" % chModelName)

                strSerialNumber = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber:
                    if per == 0:
                        break
                    strSerialNumber = strSerialNumber + chr(per)
                print("user serial number: %s" % strSerialNumber)
                devList.append("[" + str(i) + "]USB: " + chUserDefinedName + " " + chModelName
                               + "(" + str(strSerialNumber) + ")")
        isEnmu = True
        enable_controls()
        devices_info()

    # 打开相机
    def open_device():
        global deviceList
        global obj_cam_operations
        global isOpen
        global devList
        global isGrabbing
        # 打开设备
        if not isOpen:
            ui.btnOpen.setToolTip("关闭设备")
            ui.btnOpen.setIcon(QIcon('./icon/plugin_break.png'))
            obj_cam_operations = []
            if deviceList.nDeviceNum < 4:
                QMessageBox.warning(mainWindow, "Error", "don't find four cameras", QMessageBox.Ok)
            ##################for i in range(4,8):
            for i in range(0, deviceList.nDeviceNum):
                cam = MvCamera()
                obj_cam_operations.append(CameraOperation(cam, deviceList, i))
                ret = obj_cam_operations[i].Open_device()
                ###############ret = obj_cam_operations[i-4].Open_device()
                if 0 != ret:
                    strError = "Open device failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    isOpen = False
                    continue
            # 设置采集模式
            mode_switch()
            # 获取参数
            get_param()
            isOpen = True
            # 控件使能
            enable_controls()
            #关闭无损压缩
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.Compression_Off()
                if 0 != ret:
                    print("关闭无损压缩失败:",ToHexStr(ret))
            # 开启使能采集控制
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.SetFreamRate_Enable(True)
                if ret != 0:
                    print("使能采集控制设置失败")
            # 字符串
            ui.labelCam1.setText(devList[0])
            ui.labelCam2.setText(devList[1])
            ui.labelCam3.setText(devList[2])
            ui.labelCam4.setText(devList[3])
            ui.comTriggerMode.addItem("软触发")
            ui.comTriggerMode.addItem("硬触发")
        # 关闭设备
        else:
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.Close_device()
                if 0 != ret:
                    print("关闭设备失败")
                    strError = "Open device failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    isOpen = False
                    continue
            isOpen = False
            isGrabbing = False
            enable_controls()
            # 字符串
            ui.labelCam1.setText("cam1")
            ui.labelCam2.setText("cam2")
            ui.labelCam3.setText("cam3")
            ui.labelCam4.setText("cam4")
            ui.btnOpen.setToolTip("打开设备")
            ui.btnOpen.setIcon(QIcon('./icon/plugin.png'))
            ui.comTriggerMode.clear()


    #切换采集模式
    def mode_switch():
        global obj_cam_operations
        global isContinueMode
        global isSoftTrigger
        ret = 0
        if isContinueMode:
            cindex = ui.comTriggerMode.currentIndex()
            if cindex == 0:
                isSoftTrigger = True
                #print("软触发")
                for obj_cam_operation in obj_cam_operations:
                    ret = obj_cam_operation.Set_trigger_mode(True, True)
                    if ret != 0:
                        strError = "Set trigger mode failed ret:" + ToHexStr(ret)
                        QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                        break
                if ret == 0:
                    # ui.btnSoftwareTrigger.setEnabled(isGrabbing)
                    ui.edtMode.setText("  触发模式")
                    isContinueMode = False
            else:
                isSoftTrigger = False
                #print("硬触发")
                for obj_cam_operation in obj_cam_operations:
                    ret = obj_cam_operation.Set_trigger_mode(True, False)
                    if ret != 0:
                        strError = "Set trigger mode failed ret:" + ToHexStr(ret)
                        QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                        break
                if ret == 0:
                    # ui.btnSoftwareTrigger.setEnabled(isGrabbing)
                    ui.edtMode.setText("  触发模式")
                    isContinueMode = False
            if ret == 0:
                for obj_cam_operation in obj_cam_operations:
                    ret = obj_cam_operation.SetFreamRate_Enable(True)
                    if ret != 0:
                        print("使能采集控制设置失败")

        else:
            ret = 0
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.Set_trigger_mode(False, None)
                if ret != 0:
                    strError = "Set continue mode failed ret:" + ToHexStr(ret) + " mode is " + str("is_trigger_mode")
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    break
            if ret == 0:
                # ui.btnSoftwareTrigger.setEnabled(False)
                ui.edtMode.setText("  连续模式")
                isContinueMode = True
                # 采集使能控制为false
                for obj_cam_operation in obj_cam_operations:
                    ret = obj_cam_operation.SetFreamRate_Enable(False)
                    if ret != 0:
                        print("使能采集控制设置失败")

        enable_controls()

    '''
    # ch:设置采集模式(连续模式)
    def set_continue_mode():
        global obj_cam_operations
        ret = 0
        for obj_cam_operation in obj_cam_operations:
            ret = obj_cam_operation.Set_trigger_mode(False)
            if ret != 0:
                strError = "Set continue mode failed ret:" + ToHexStr(ret) + " mode is " + str("is_trigger_mode")
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
        if ret == 0:
            ui.radioContinueMode.setChecked(True)
            ui.radioTriggerMode.setChecked(False)
            ui.btnSoftwareTrigger.setEnabled(False)

    # ch:设置采集模式(触发模式)
    def set_software_trigger_mode():
        global obj_cam_operations
        ret = 0
        for obj_cam_operation in obj_cam_operations:
            ret = obj_cam_operation.Set_trigger_mode(True)
            if ret != 0:
                strError = "Set trigger mode failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                break
        if ret == 0:
            ui.radioContinueMode.setChecked(False)
            ui.radioTriggerMode.setChecked(True)
            ui.btnSoftwareTrigger.setEnabled(isGrabbing)
    '''

    # 切换软触发，硬触发
    def select_trigger_mode():
        global isSoftTrigger
        global comSel
        global isContinueMode
        cindex = ui.comTriggerMode.currentIndex()
        ret = 0
        if comSel == cindex:
            print("选择相同")
            return
        if cindex == 0:
            isSoftTrigger = True
            # print("软触发")
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.Set_trigger_mode(True, True)
                if ret != 0:
                    strError = "Set trigger mode failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    break
            if ret == 0:
                # ui.btnSoftwareTrigger.setEnabled(isGrabbing)
                ui.edtMode.setText("  触发模式")
                isContinueMode = False
        else:
            isSoftTrigger = False
            # print("硬触发")
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.Set_trigger_mode(True, False)
                if ret != 0:
                    strError = "Set trigger mode failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    break
            if ret == 0:
                # ui.btnSoftwareTrigger.setEnabled(isGrabbing)
                ui.edtMode.setText("  触发模式")
                isContinueMode = False
        comSel = cindex

    # 开始采集，停止采集。采集不成功，尝试关闭防火墙。
    def grabbing():
        global obj_cam_operations
        global isGrabbing
        global isCompression
        global timer_info
        global counter_info
        ret =0
        # 停止采集
        if isGrabbing:
            for i in range(0, len(obj_cam_operations)):
                if 0 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                elif 1 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                elif 2 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                elif 3 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                if 0 != ret:
                    strError = "cam" + str(i + 1) + "Stop grabbing failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    break
            if ret == 0:
                isGrabbing = False
                enable_controls()
                ui.btnStart.setToolTip("开始采集")
                ui.btnStart.setIcon(QIcon("./icon/play.png"))
                timer_info.stop()
                ui.tabDevicesInfo.setItem(13, 1, QTableWidgetItem(""))
        # 开始采集
        else:
            for i in range(0, len(obj_cam_operations)):
                if 0 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay1.winId(), False, None, isCompression)
                elif 1 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay2.winId(), False, None, isCompression)
                elif 2 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay3.winId(), False, None, isCompression)
                elif 3 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay4.winId(), False, None, isCompression)
                if 0 != ret:
                    strError = "cam" + str(i + 1) + "Start grabbing failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    break
            if ret == 0:
                ui.tabDevicesInfo.setItem(11, 1, QTableWidgetItem("0,0,0,0"))
                ui.tabDevicesInfo.setItem(12, 1, QTableWidgetItem("0,0,0,0"))
                isGrabbing = True
                enable_controls()
                ui.btnStart.setToolTip("停止采集")
                ui.btnStart.setIcon(QIcon("./icon/pause.png"))
                timer_info.start(2000)
                counter_info.restart()
    '''
    # ch:开始取流 | en:Start grab image
    def start_grabbing():
        global obj_cam_operations
        global isGrabbing
        ret = 0
        for i in range(0,len(obj_cam_operations)):
            if 0 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay1.winId(), False, None)
            elif 1 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay2.winId(), False, None)
            elif 2 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay3.winId(), False, None)
            elif 3 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay4.winId(), False, None)
            if 0 != ret:
                strError = "cam" + str(i+1) + "Start grabbing failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                break
        if ret == 0:
            isGrabbing = True
            enable_controls()

    # 停止取流
    def stop_grabbing():
        global obj_cam_operations
        global isGrabbing
        global isGrabbingAndSave
        global timer
        if isGrabbingAndSave:
            timer.stop()
        ret = 0
        for i in range(0,len(obj_cam_operations)):
            if 0 == i:
                ret = obj_cam_operations[i].Stop_grabbing()
            elif 1 == i:
                ret = obj_cam_operations[i].Stop_grabbing()
            elif 2 == i:
                ret = obj_cam_operations[i].Stop_grabbing()
            elif 3 == i:
                ret = obj_cam_operations[i].Stop_grabbing()
            if 0 != ret:
                strError = "cam" + str(i+1) + "Stop grabbing failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                break
        if ret == 0:
            isGrabbing = False
            isGrabbingAndSave = False
            enable_controls()
    '''

    # 触发一次
    def trigger_once():
        global bTriggerOnce
        global obj_cam_operations
        ret = 0
        for obj_cam_operation in obj_cam_operations:
            ret = obj_cam_operation.Trigger_once()
            if ret != 0:
                strError = "TriggerSoftware failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                break
        if ret == 0:
            bTriggerOnce = True
            enable_controls()


    # ch: 获取参数 | en:get param
    def get_param():
        global obj_cam_operations
        ret = obj_cam_operations[0].Get_parameter()
        if ret != MV_OK:
            strError = "Get param failed ret:" + ToHexStr(ret)
            QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
        else:
            # 展示帧率
            ui.edtFrameRate.setText("{0:.2f}".format(obj_cam_operations[0].frame_rate))
            # 曝光时间
            ui.edtExposureTime.setText("{0:.2f}".format(obj_cam_operations[0].exposure_time))
            ui.edtImageWidth.setText(str(obj_cam_operations[0].image_width))
            ui.edtImageHeight.setText(str(obj_cam_operations[0].image_height))
            ui.edtMaxFrameRate.setText("{0:.2f}".format(obj_cam_operations[0].resulting_frame_rate))

    # ch: 通过是否开启设备，是否开始采集，设置控件状态
    def enable_controls():
        global isGrabbing
        global isOpen
        global isEnmu

        # 先设置group的状态，再单独设置各控件状态
        # ui.groupGrab.setEnabled(isOpen)
        #ui.groupParam.setEnabled(isOpen and not isGrabbing)
        ui.btnSetParam.setEnabled(isOpen and not isGrabbing)
        ui.btnCompression.setEnabled(isOpen and not isGrabbing)
        ui.btnGetParam.setEnabled(isOpen)

        ui.btnOpen.setEnabled(isEnmu)
        ui.btnModeSwitch.setEnabled(isOpen and (not isGrabbing) and (not isRecording))
        ui.btnStart.setEnabled(isOpen and not isRecording)
        # ui.btnStop.setEnabled(isOpen and (isGrabbing or isGrabbingAndSave))
        ui.btnSoftwareTrigger.setEnabled((isGrabbing or isRecording) and (not isContinueMode) and isSoftTrigger)

        ui.btnSaveImage.setEnabled(isGrabbing and (not isSoftTrigger or bTriggerOnce))
        # ui.btnSaveAcquisition.setEnabled(isOpen and (not isGrabbing) and (not isRecording)) # 新增采集保存按钮
        ui.btnRecording.setEnabled(isOpen and not isGrabbing)
        ui.edtMaxFrameRate.setEnabled(False)
        ui.comTriggerMode.setEnabled(isOpen and not isContinueMode and not isGrabbing)


    # 设置保存路径
    def set_path():
        global savePath
        getPath = QFileDialog.getExistingDirectory(None, "选择保存目录")
        if getPath != '':
            savePath = getPath
            ui.edtFilePath.setText(savePath)

    #录制
    def recording():
        global isRecording
        global obj_cam_operations
        global timer
        global counter
        global timer_info
        global counter_info
        global savePath
        global isCompression
        ret =0
        # 停止采集
        if isRecording:
            timer.stop()
            timer_info.stop()
            ui.tabDevicesInfo.setItem(13, 1, QTableWidgetItem(""))
            for i in range(0, len(obj_cam_operations)):
                if 0 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                elif 1 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                elif 2 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                elif 3 == i:
                    ret = obj_cam_operations[i].Stop_grabbing()
                if 0 != ret:
                    strError = "cam" + str(i + 1) + "Stop grabbing failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    break
            if ret == 0:
                isRecording = False
                enable_controls()
                ui.labShowTime.setText(None)

        # 开始采集
        else:
            for i in range(0, len(obj_cam_operations)):
                if 0 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay1.winId(), True, savePath + "/0", isCompression)
                elif 1 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay2.winId(), True, savePath + "/1", isCompression)
                elif 2 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay3.winId(), True, savePath + "/2", isCompression)
                elif 3 == i:
                    ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay4.winId(), True, savePath + "/3", isCompression)
                if 0 != ret:
                    strError = "cam" + str(i + 1) + "Start grabbing failed ret:" + ToHexStr(ret)
                    QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                    break
            if ret != 0:
                strError = "Start grabbing failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
            else:
                ui.tabDevicesInfo.setItem(11, 1, QTableWidgetItem("0,0,0,0"))
                ui.tabDevicesInfo.setItem(12, 1, QTableWidgetItem("0,0,0,0"))
                isRecording = True
                enable_controls()
                timer.start(1000)  # 启动定时器，每隔1秒超时一次
                counter.restart()  # 开始计时restart
                timer_info.start(2000)
                counter_info.restart()
                ui.btnRecording.setIcon(QIcon("./icon/video-record_on.png"))

    '''
    # 采集保存
    def grabbing_save():
        global isGrabbingAndSave
        global obj_cam_operations
        global timer
        global counter
        global savePath
        # ret = obj_cam_operations.Start_grabbing(ui.widgetDisplay1.winId(), True)
        ret = 0
        for i in range(0,len(obj_cam_operations)):
            if 0 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay1.winId(), True, savePath+"/0")
            elif 1 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay2.winId(), True, savePath+"/1")
            elif 2 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay3.winId(), True, savePath+"/2")
            elif 3 == i:
                ret = obj_cam_operations[i].Start_grabbing(ui.widgetDisplay4.winId(), True, savePath+"/3")
            if 0 != ret:
                strError = "cam" + str(i+1) + "Start grabbing failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                break
        if ret != 0:
            strError = "Start grabbing failed ret:" + ToHexStr(ret)
            QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
        else:
            isGrabbingAndSave = True
            enable_controls()
            timer.start(1000)  # 启动定时器，每隔1秒超时一次
            counter.restart()  # 开始计时restart
    '''
    # 保存图片
    def save_image():
        global obj_cam_operations
        global bTriggerOnce
        global savePath
        ret = 0
        if isSoftTrigger and not bTriggerOnce:
            QMessageBox.warning(mainWindow, "Error", "don not trigger once ", QMessageBox.Ok)
        else:
            for i in range(0, len(obj_cam_operations)):
                if 0 == i:
                    ret = obj_cam_operations[i].Save_jpg(savePath+"/0")
                elif 1 == i:
                    ret = obj_cam_operations[i].Save_jpg(savePath+"/1")
                elif 2 == i:
                    ret = obj_cam_operations[i].Save_jpg(savePath + "/2")
                elif 3 == i:
                    ret = obj_cam_operations[i].Save_jpg(savePath + "/3")
                if ret != MV_OK:
                    break
            if ret != MV_OK:
                strError = "Save jpg failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
            else:
                print("Save image success")

    # 设置参数
    def set_param():
        global obj_cam_operations
        ret = 0
        frame_rate = ui.edtFrameRate.text()
        # max_frame_rate = ui.edtMaxFrameRate.text()
        '''
        if float(frame_rate) > float(max_frame_rate):
            print("设置帧率超出范围")
            frame_rate = int(float(max_frame_rate))
            ui.edtFrameRate.setText(str(frame_rate)+".00")
        '''
        exposure_time = ui.edtExposureTime.text()
        image_width = ui.edtImageWidth.text()
        image_height = ui.edtImageHeight.text()
        for i in range(0, len(obj_cam_operations)):
            if 0 == i:
                ret = obj_cam_operations[i].Set_parameter(frame_rate, exposure_time, image_width, image_height)
            elif 1 == i:
                ret = obj_cam_operations[i].Set_parameter(frame_rate, exposure_time, image_width, image_height)
            elif 2 == i:
                ret = obj_cam_operations[i].Set_parameter(frame_rate, exposure_time, image_width, image_height)
            elif 3 == i:
                ret = obj_cam_operations[i].Set_parameter(frame_rate, exposure_time, image_width, image_height)
            if 0 != ret:
                strError = "cam" + str(i+1) + "Set parameter failed ret:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                break

    #定时器，计时器
    def timer_timeout():
        global counter
        totals = counter.elapsed() // 1000  #返回总秒数
        strSecond = "%02d"%(totals%60)
        strMinute = "%02d"%((totals//60)%60)
        strHour = "%02d"%(totals//60//60)
        strShowTime = strHour + ":" + strMinute + ":" + strSecond
        ui.labShowTime.setText(strShowTime)

    #无损压缩
    def compression():
        global isCompression
        global obj_cam_operations
        ret = 0
        if isCompression:
            # print("关闭无损压缩")
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.Compression_Off()
                if ret != 0:
                    strError = "trun on compression mode failed:" + ToHexStr(ret)
                    print(strError)
                    break
            if ret != 0:
                strError = "trun off compression mode failed:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
            else:
                isCompression = False
                ui.btnCompression.setIcon(QIcon('./icon/controls_off.png'))
                ui.btnCompression.setToolTip("无损压缩:关闭")
        else:
            # print("开启无损压缩")
            for obj_cam_operation in obj_cam_operations:
                ret = obj_cam_operation.Compression_On()
                if ret != 0:
                    break
            if ret!= 0:
                strError = "trun on compression mode failed:" + ToHexStr(ret)
                QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
            else:
                isCompression = True
                ui.btnCompression.setIcon(QIcon('./icon/controls_on.png'))
                ui.btnCompression.setToolTip("无损压缩:打开")


    # 设备信息
    def devices_info():
        global devInfo
        ui.tabDevicesInfo.setItem(1, 1, QTableWidgetItem(devInfo['ip'][0]))
        ui.tabDevicesInfo.setItem(2, 1, QTableWidgetItem(devInfo['ip'][1]))
        ui.tabDevicesInfo.setItem(3, 1, QTableWidgetItem(devInfo['ip'][2]))
        ui.tabDevicesInfo.setItem(4, 1, QTableWidgetItem(devInfo['ip'][3]))
        ui.tabDevicesInfo.setItem(5, 1, QTableWidgetItem(devInfo['MAC'][0]))
        ui.tabDevicesInfo.setItem(6, 1, QTableWidgetItem(devInfo['MAC'][1]))
        ui.tabDevicesInfo.setItem(7, 1, QTableWidgetItem(devInfo['MAC'][2]))
        ui.tabDevicesInfo.setItem(8, 1, QTableWidgetItem(devInfo['MAC'][3]))
        ui.tabDevicesInfo.setItem(9, 1, QTableWidgetItem(devInfo['ModeName']))
        ui.tabDevicesInfo.setItem(10, 1, QTableWidgetItem(devInfo['VendorName']))

    # 查询采集信息,2s更新一次,接收总帧数，丢帧数量
    def acq_info():
        global recvFrameCount
        strThrowFrame = ""
        strRecvFrame = ""
        for i in range(0, len(obj_cam_operations)):
            ret, nThrowFrameCount, nNetRecvFrameCount = obj_cam_operations[i].Acquisition_info()
            if ret != 0:
                strError = "Real-time information query failed:" + ToHexStr(ret)
                # QMessageBox.warning(mainWindow, "Error", strError, QMessageBox.Ok)
                print(strError)
                break
            else:
                strThrowFrame = strThrowFrame + str(nThrowFrameCount) + ","
                strRecvFrame = strRecvFrame + str(nNetRecvFrameCount) + ","
            if i == 0:
                addFrame = nNetRecvFrameCount - recvFrameCount
                ui.tabDevicesInfo.setItem(13, 1, QTableWidgetItem(str(addFrame/2)))
                recvFrameCount = nNetRecvFrameCount
                print("recvFrameCount:", recvFrameCount, "nNetRecvFrameCount:", nNetRecvFrameCount, "FrameRate:", str(addFrame/2))
        if ret == 0:
            ui.tabDevicesInfo.setItem(11, 1, QTableWidgetItem(strRecvFrame[0:-1]))
            ui.tabDevicesInfo.setItem(12, 1, QTableWidgetItem(strThrowFrame[0:-1]))


    app = QApplication(sys.argv)
    mainWindow = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(mainWindow)
    styleFile = 'qss.css'
    qssStyle = CommonHelper.readQSS(styleFile)
    mainWindow.setStyleSheet(qssStyle)

    enable_controls()

    ui.edtFilePath.setText(savePath)

    # 事件绑定,分组
    timer.timeout.connect(timer_timeout)
    timer_info.timeout.connect(acq_info)
    ui.btnEnum.clicked.connect(enum_devices)
    ui.btnEnum.setToolTip("查找设备")
    ui.btnOpen.clicked.connect(open_device)
    ui.btnOpen.setToolTip("打开设备")

    # ui.radioContinueMode.clicked.connect(set_continue_mode)
    # ui.radioTriggerMode.clicked.connect(set_software_trigger_mode)
    ui.btnModeSwitch.clicked.connect(mode_switch)
    ui.btnModeSwitch.setToolTip("切换采集模式")
    ui.edtMode.setEnabled(False)
    ui.comTriggerMode.activated.connect(select_trigger_mode)
    ui.btnSoftwareTrigger.clicked.connect(trigger_once)
    ui.btnSoftwareTrigger.setToolTip("触发一次")
    ui.btnStart.clicked.connect(grabbing)
    ui.btnStart.setToolTip("开始采集")
    # ui.btnStop.clicked.connect(stop_grabbing)
    # ui.btnStop.setToolTip("停止采集")

    ui.btnSaveImage.clicked.connect(save_image)
    ui.btnSaveImage.setToolTip("保存图片")
    ui.btnRecording.clicked.connect(recording)
    ui.btnRecording.setToolTip("开始录制")
    # ui.btnSaveAcquisition.clicked.connect(grabbing_save)
    # ui.btnSaveAcquisition.setToolTip("开始录制")
    ui.btnPath.clicked.connect(set_path)
    ui.btnPath.setToolTip("保存路径")

    ui.edtImageWidth.setToolTip("最大宽度:" + str(maxImgWeight))
    ui.edtImageHeight.setToolTip("最大高度:" + str(maxImgHeight))
    ui.btnCompression.clicked.connect(compression)
    ui.btnCompression.setToolTip("无损压缩:关闭")
    ui.btnGetParam.clicked.connect(get_param)
    ui.btnSetParam.clicked.connect(set_param)

    # 设备信息表格
    ui.tabDevicesInfo.setColumnWidth(0, 80)
    ui.tabDevicesInfo.setColumnWidth(1, 140)




    mainWindow.show()

    app.exec_()
    sys.exit()