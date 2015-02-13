#include <iostream>
#include <fstream>
#include <stdio.h>
#include <string.h>
#include <okFrontPanelDLL.h>
#include <Windows.h>


#define ALTERA_CONFIGURATION_FILE  "finalv3_1_top.rbf" //C:\altera\Projects\finalv3\output_files\

#define BITFILE_NAME           "finalv3_1_top.rbf"
#define MIN(a,b)               ((a)<(b) ? (a) : (b))
#define BUFFER_SIZE            (16*1024)
#define MAX_TRANSFER_SIZE      1024
#define FLASH_PAGE_SIZE        256
#define FLASH_SECTOR_SIZE      (65536)


int main()
{
	okCFrontPanel *dev;
	dev = new okCFrontPanel;

	okTDeviceInfo m_devInfo;
	//okTDeviceInfo  *m_devInfo;
	//m_devInfo = new okTDeviceInfo;

	std::string config_filename = ALTERA_CONFIGURATION_FILE;

	printf("---- Opal Kelly ---- FPGA-DES Application v1.0 ----\n");
	printf("---------------------------------------------------\n");
	printf("--------------Initialising Device------------------\n");
	if (FALSE == okFrontPanelDLL_LoadLib(NULL)) {
		printf("FrontPanel DLL could not be loaded.\n");
		return(-1);
	}

	if (okCFrontPanel::NoError != dev->OpenBySerial()) {
		delete dev;
		printf("Device could not be opened.  Is one connected?\n");
		return(NULL);
	}

	dev->GetDeviceInfo(&m_devInfo);
	
	// Download the configuration file.
	if (okCFrontPanel::NoError != dev->ConfigureFPGA(std::string(config_filename))) {
		printf("FPGA configuration failed.\n");
		return(false);
	}

	printf("-------------- Accessing Flash --------------------\n");

	// If no command line arguments are given, we clear the Reset Profile for USB 3.0 deviecs.
	printf("Clearing Boot Reset Profile.\n");
	okTFPGAResetProfile oldprofile;
	memset(&oldprofile, 0, sizeof(okTFPGAResetProfile));
	dev->SetFPGAResetProfile(ok_FPGAConfigurationMethod_NVRAM, &oldprofile);

	if (0 == m_devInfo.flashFPGA.sectorCount) 
		printf("This device does not have an FPGA flash.\n");
	else 
		printf("Available Flash: %d Mib\n", m_devInfo.flashFPGA.sectorCount * m_devInfo.flashFPGA.sectorSize * 8 / 1024 / 1024);

	std::ifstream bit_in;
	unsigned char buf[BUFFER_SIZE];
	int i, j, k;
	long lN;

	bit_in.open(BITFILE_NAME, std::ios::binary);
	if (false == bit_in.is_open()) 
	{
		printf("Error: Bitfile could not be opened.\n");
		return(false);
	}

	bit_in.seekg(0, std::ios::end);
	lN = (long)bit_in.tellg();
	bit_in.seekg(0, std::ios::beg);

	
	// Verify that the file will fit in the available flash.
	if ((UINT32)lN > m_devInfo.flashFPGA.sectorCount * m_devInfo.flashFPGA.sectorSize) {
		printf("Error: File size exceeds available flash memory.\n");
		printf("Consider enabling bitstream compression when generating a bitfile.\n");
		return(false);
	}

	
	i = (lN-1) / m_devInfo.flashSystem.sectorSize + 1;
	for (j=0; j<i; j++) 
	{
		std::cout << "Erasing sector " << (j+m_devInfo.flashSystem.minUserSector) << std::endl;
		//printf("Erasing sector %d\r", (j+m_devInfo.flashSystem.minUserSector));
		fflush(stdout);
		dev->FlashEraseSector((j+m_devInfo.flashSystem.minUserSector) * m_devInfo.flashSystem.sectorSize);
	}
	std::cout << "Erasing done." << std::endl;

	int count;
	j = lN;
	k = m_devInfo.flashSystem.minUserSector * m_devInfo.flashSystem.sectorSize;
	while (j>0) 
	{
		std::cout << "Writing to address : " << std::cout << "0x" << std::hex << k << std::endl;
		fflush(stdout);
		count = MIN(j, (int)m_devInfo.flashSystem.pageSize);
		bit_in.read((char *)buf, count);
		dev->FlashWrite(k, m_devInfo.flashSystem.pageSize, buf);
		k += count;
		j -= count;
	}
	

	printf("Setting up Boot Reset Profile.\n");
	okTFPGAResetProfile profile;
	memset(&profile, 0, sizeof(okTFPGAResetProfile));
	profile.configFileLocation = m_devInfo.flashSystem.minUserSector;
	profile.configFileLength = lN;
	profile.doneWaitUS = 1000;
	profile.wireInValues[0] = 0x00000000;
	profile.wireInValues[1] = 0x40000000;
	profile.wireInValues[2] = 0x00000000;
	profile.wireInValues[3] = 0x00000000;
	profile.wireInValues[4] = 0x00000000;
	profile.wireInValues[5] = 0x00000000;
	profile.wireInValues[6] = 0x00000064;
	profile.registerWaitUS = 10000;
	//std::cout << "test:" << std::endl << "length: " << lN << " location: " << m_devInfo.flashSystem.minUserSector << std::endl;
	dev->SetFPGAResetProfile(ok_FPGAConfigurationMethod_NVRAM, &profile);
	std::cout << "Done.";
	return(0);
}