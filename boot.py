import usb_hid
import storage

# This is only one example of a gamepad descriptor, and may not suit your needs.
GAMEPAD_REPORT_DESCRIPTOR = bytes((
    0x05, 0x01,    # UsagePage(Generic Desktop[0x0001])
    0x09, 0x05,    # Usage (Game Pad)
    0xA1, 0x01,    # Collection(Application)
    0x85, 0x09,    #     ReportId(9)
    0x05, 0x09,    #     UsagePage(Button[0x0009])
    0x19, 0x01,    #     UsageIdMin(Button 1[0x0001])
    0x29, 0x20,    #     UsageIdMax(Button 32[0x0020])
    0x15, 0x00,    #     LogicalMinimum(0)
    0x25, 0x01,    #     LogicalMaximum(1)
    0x75, 0x01,    #     ReportSize(1)
    0x95, 0x20,    #     ReportCount(32)
    0x81, 0x02,    #     Input(Data, Variable, Absolute, NoWrap, Linear, PreferredState, NoNullPosition, BitField)
    0xC0,          # EndCollection()
))


gamepad = usb_hid.Device(
    report_descriptor=GAMEPAD_REPORT_DESCRIPTOR,
    usage_page=0x01,           # Generic Desktop Control
    usage=0x05,                # Gamepad
    report_ids=(9,),           # Descriptor uses report ID 9.
    in_report_lengths=(4,),    # This gamepad sends 4 bytes in its report.
    out_report_lengths=(0,),   # It does not receive any reports.
)

#storage.disable_usb_drive()  # Disable storage to enable HID
storage.remount("/", readonly=False)
usb_hid.enable(
     (gamepad, )
)
