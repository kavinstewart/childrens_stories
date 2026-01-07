#import "ObjCExceptionCatcher.h"

@implementation ObjCExceptionCatcher

+ (BOOL)tryBlock:(void(NS_NOESCAPE ^)(void))tryBlock
           error:(NSError * _Nullable __autoreleasing * _Nullable)error {
    @try {
        tryBlock();
        return YES;
    } @catch (NSException *exception) {
        if (error) {
            NSMutableDictionary *userInfo = [NSMutableDictionary dictionary];
            if (exception.reason) {
                userInfo[NSLocalizedDescriptionKey] = exception.reason;
            }
            if (exception.userInfo) {
                userInfo[@"ExceptionUserInfo"] = exception.userInfo;
            }
            *error = [NSError errorWithDomain:@"ObjCExceptionDomain"
                                         code:1
                                     userInfo:userInfo];
        }
        return NO;
    }
}

@end
