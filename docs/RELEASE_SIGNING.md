# Signing a Fable build for the Meta dashboard (route B)

The first upload to the Meta Horizon Developer Dashboard was signed on another laptop. Meta only accepts updates signed
with that same key, so a build made anywhere else is re-signed on that laptop before upload. The version code is set in
`unity/Fable/Assets/Fable/Editor/FableBuild.cs` (`bundleVersionCode`, yyyymmddNN) and must grow with every upload.

## On the laptop that holds the key

You need: the APK (`fable.apk`, about 820 MB), the keystore (`.keystore` or `.jks`), its alias and its passwords. Unity's
Android module already includes everything else. Paths below are for a Mac with Unity 6000.3.27f2; on Windows use the
same folders under `C:\Program Files\Unity\Hub\Editor\<version>\Editor\Data\PlaybackEngines\AndroidPlayer\` and the
`.bat` versions of the tools.

1. Open Terminal and point it at Unity's Android tools (change the version if the laptop has another Unity 6):

   ```
   U=/Applications/Unity/Hub/Editor/6000.3.27f2/PlaybackEngines/AndroidPlayer
   export JAVA_HOME="$U/OpenJDK"
   BT=$(ls -d "$U"/SDK/build-tools/* | tail -1)
   ```

2. Find the alias in the keystore if you don't know it (asks for the keystore password):

   ```
   "$JAVA_HOME/bin/keytool" -list -keystore /path/to/your.keystore
   ```

3. Sign (asks for the keystore password, then the key password; they are often the same):

   ```
   "$BT/apksigner" sign --ks /path/to/your.keystore --ks-key-alias YOUR_ALIAS --out fable-signed.apk fable.apk
   ```

4. Check it worked. The certificate printed should be the one the earlier upload used:

   ```
   "$BT/apksigner" verify --print-certs fable-signed.apk
   ```

5. Upload `fable-signed.apk` in the dashboard: your app, Distribution, Release channels, **Competition**, upload a new
   build. Keep the same release channel so the existing invite link gives judges the new version.

If the dashboard says the signature does not match, the keystore is not the one used for the first upload. If it says the
version code must be higher, raise `bundleVersionCode` in FableBuild.cs, rebuild and sign again.

Never commit the keystore or put its passwords in the repo or in chat.
